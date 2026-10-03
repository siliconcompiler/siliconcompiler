'''
A job's Python packages, installed while it stages: on the host, or built into
an image a node resolved to.
'''

import json
import os
import shutil

from typing import Any, Dict, List, Tuple

from siliconcompiler.remote import environment
from siliconcompiler.remote.server.jobs.common import (
    _Absent, _NoLongerStaging, _ServerFailure, _StagingTimedOut, _bounded, _build_refusal,
    _install_lines, _python_names, _sent_back_for, logger)
from siliconcompiler.remote.server.outputs import record
from siliconcompiler.remote.server.running.dispatch import DispatchError
from siliconcompiler.remote.server.software import images


# Where host mode keeps the environments it installs, each named by its key.
ENVIRONMENTS = "python-envs"


class PythonEnvMixin:
    '''A job's Python packages, installed while it stages.'''

    def _python_install(self, job, summary):
        '''``(packages, wheels)`` to install, the lists less what each wheel
        replaces; None where no node runs the user's Python or there is no
        requirement and no wheel.'''
        if not summary["python"]:
            return None
        unpacked = self.job_root(job["user_id"], job["id"]) / job["design"] / job["jobname"]
        top = unpacked / environment.wheels_path()
        wheels = sorted(str(path) for path in top.glob("*.whl")) if top.is_dir() else []
        packages = environment.parse(json.loads(job["python_packages"])) \
            if job["python_packages"] else environment.Packages()
        packages = packages.without(environment.wheel_name(path) for path in wheels)
        if not packages.requirements and not wheels:
            return None
        return packages, wheels

    def _install_on_host(self, job, summary) -> List[str]:
        '''Host mode: install the job's Python packages into the environment of
        their key and link it into the job's tree. Returns each package no index
        has, for which the job is sent back.

        A package that will not install rejects the job before any node runs;
        an index that does not answer is `staging-failed`.
        '''
        from siliconcompiler.remote.server.packages import envinstall

        if self._config["containers"] or "python.env" not in (self._config["features"] or ()):
            return []
        wanted = self._python_install(job, summary)
        if wanted is None:
            return []
        packages, wheels = wanted

        self._phase(job["id"], "installing the job's Python packages")
        root = self.job_root(job["user_id"], job["id"])
        try:
            # An environment per key, never one per user: two jobs never
            # write one at once, and a finished one is reused as a layer is.
            target, installed = envinstall.install(
                packages, wheels, self._datadir / ENVIRONMENTS, logger,
                constrain=_python_names(job),
                indexes=list(self._config["package_indexes"] or []),
                timeout=max(1, self._staging_left(job["id"])),
                # pip's own output, whole, for the operators.
                echo=lambda said: record.keep(root, "builder.log", said))
        except envinstall.InstallFailed as e:
            if e.result.get("timed_out"):
                raise _StagingTimedOut("installing the job's Python packages") from None
            if e.result.get("absent") or e.result.get("source_only"):
                return _sent_back_for(e.result, packages)
            if e.result.get("network") or e.result.get("returncode") == -1:
                raise _ServerFailure(_bounded(
                    "the install of the job's Python packages could not reach an "
                    f"index:\n{e.result.get('tail', '')}")) from None
            raise self._refuse_staging(job, _build_refusal(packages, e.result)) from None

        unpacked = self.job_root(job["user_id"], job["id"]) / job["design"] / job["jobname"]
        link = unpacked / environment.site_path()
        link.parent.mkdir(exist_ok=True)
        if link.is_symlink() or link.is_file():
            link.unlink()
        link.symlink_to(target, target_is_directory=True)

        # No image on the host, so the `staging` record is the record of what
        # the install added (PROFILE.md section 5).
        self._note(job, _install_lines(installed, "this host"))
        if self._row(job["id"])["state"] != "staging":
            raise _NoLongerStaging(job["id"])
        return []

    def _build_environments(self, job, summary, plan):
        '''``(plan, absent)``: ``plan`` with each node running the user's Python
        moved onto an image of the job's packages over its base, one per base
        and reused; or ``plan`` unchanged and each package no index has.

        A package that will not install rejects the job from `staging`.
        '''
        from siliconcompiler.remote.server.packages import envinstall

        if not (self._config["containers"] and self._config["env_builder"]):
            return plan, []
        wanted = self._python_install(job, summary)
        if wanted is None:
            return plan, []
        packages, wheels = wanted
        inputs = {"packages": packages, "wheels": wheels,
                  "requirements": environment.render(packages.requirements,
                                                     header=envinstall.HEADER),
                  "constraints": environment.render(packages.constraints,
                                                    header=envinstall.HEADER)}
        digests = [envinstall.digest(path) for path in wheels]

        nodes, refs = dict(plan.nodes), dict(plan.refs)
        done: Dict[str, Tuple[str, str]] = {}
        for node in sorted(summary["python"]):
            base_id = nodes.get(node)
            base_ref = refs.get(base_id) if base_id else None
            if not base_ref:
                raise _ServerFailure(f"{node[0]}/{node[1]} has no image to install the "
                                     "job's Python packages on")
            key = images.derivation(base_ref.split("@", 1)[1], inputs["requirements"],
                                    inputs["constraints"], digests, _python_names(job),
                                    indexes=list(self._config["package_indexes"] or []),
                                    source_builds=self._config["python_source_builds"])
            if key not in done:
                try:
                    done[key] = self._derived_for(job, node, base_id, base_ref, key, inputs)
                except _Absent as e:
                    return plan, e.asked
            image_id, ref = done[key]
            nodes[node] = image_id
            refs[image_id] = ref
        return images.Plan(plan.job, nodes, refs), []

    def _derived_for(self, job, node, base_id, base_ref, key, inputs) -> Tuple[str, str]:
        '''The derived image for one base and key, as (id, pinned ref).'''
        import threading

        def found():
            row = images.derived_image(self._store, base_id, key)
            return (row["id"], images.pinned_ref(row["registry_ref"], row["digest"])) \
                if row else None

        existing = found()
        if existing:
            return existing

        with self._building_lock:
            lock = self._building.setdefault(key, threading.Lock())
        with lock:
            existing = found()
            if existing:
                return existing
            result = self._run_build(job, node, base_ref, key, inputs)
            image_id = images.register_derived(
                self._store, base_id, result["ref"], result["digest"], key,
                [tuple(pair) for pair in result.get("installed") or []],
                note=f"the Python packages of job {job['id']}, on "
                     f"{result.get('python')} ({result.get('platform')})")
            logger.info(f"{job['id']}: built its Python packages on {base_ref} as "
                        f"{result['ref']}")
            self._note(job, _install_lines(result, base_ref))
            return image_id, images.pinned_ref(result["ref"], result["digest"])

    def _run_build(self, job, node, base_ref, key, inputs) -> Dict[str, Any]:
        '''One build, as a job of its own in the builder queue; its result, or
        the job refused. Raises _Absent for a package no index has.'''
        import uuid

        from siliconcompiler.remote.server.packages import envbuild

        workspace = self._datadir / "envbuilds" / f"{key[:16]}-{uuid.uuid4().hex[:8]}"
        workspace.mkdir(parents=True)
        try:
            (workspace / envbuild.REQUIREMENTS).write_text(inputs["requirements"])
            (workspace / envbuild.CONSTRAINTS).write_text(inputs["constraints"])
            if inputs["wheels"]:
                (workspace / envbuild.WHEELS).mkdir()
                for wheel in inputs["wheels"]:
                    shutil.copy(wheel, workspace / envbuild.WHEELS / os.path.basename(wheel))
            # What is left of this staging pass.
            timeout = max(1, int(self._staging_left(job["id"])))
            (workspace / envbuild.SPEC).write_text(json.dumps({
                "key": key, "base_ref": base_ref, "base_digest": base_ref.split("@", 1)[1],
                "bundles_root": str(self.bundles_root()), "mounts": self.container_mounts(),
                "index_allowlist": list(self._config["index_allowlist"] or []),
                # Where pip looks: the deployment's, never the job's.
                "indexes": list(self._config["package_indexes"] or []),
                "source_builds": bool(self._config["python_source_builds"]),
                "timeout": timeout,
                "comment": f"sc-server: a job's Python packages ({key[:12]})",
            }, indent=1))

            try:
                build_id = self._dispatcher.submit_build(
                    key[:12], workspace, workspace / envbuild.SPEC,
                    queue=self._config["build_queue"])
            except DispatchError as e:
                raise _ServerFailure(f"this server could not start the build of the job's "
                                     f"Python packages on {base_ref}: {e}") from None
            logger.info(f"{job['id']}: building its Python packages for "
                        f"{node[0]}/{node[1]}'s image as {build_id}")

            # A cancel stops the build.
            result = envbuild.wait_for(
                workspace, timeout,
                alive=lambda: self._dispatcher.is_alive(build_id)
                and self._row(job["id"])["state"] == "staging",
                **self._build_wait)
            if self._row(job["id"])["state"] != "staging":
                self._dispatcher.cancel(build_id)
                raise _NoLongerStaging(job["id"])
            if result is None:
                self._dispatcher.cancel(build_id)
                if self._staging_left(job["id"]) <= 1:
                    raise _StagingTimedOut(
                        f"building the job's Python packages on {base_ref}")
                # Gone with time to spare: lost, this server's failure.
                log = workspace / envbuild.LOG
                tail = "\n".join(log.read_text(errors="replace").strip().splitlines()[-10:]) \
                    if log.is_file() else ""
                raise _ServerFailure(_bounded(
                    f"the build of the job's Python packages on {base_ref} was lost "
                    "before it finished" + (f":\n{tail}" if tail else "")))
            if not result.get("ok") and result.get("reason") == "absent":
                raise _Absent(_sent_back_for(result, inputs["packages"]))
            if not result.get("ok") and result.get("reason") != "uninstallable":
                raise _ServerFailure(_bounded(
                    f"this server could not build the job's Python packages on "
                    f"{base_ref}: {result.get('detail') or 'the build failed'}"))
            if not result.get("ok"):
                raise self._refuse_staging(
                    job, _build_refusal(inputs["packages"], result,
                                        where=f" on {node[0]}/{node[1]}'s image"))
            return result
        finally:
            # The builder's own output, whole, for the operators.
            log = workspace / envbuild.LOG
            if log.is_file():
                record.keep(self.job_root(job["user_id"], job["id"]), "builder.log",
                            f"==> the build on {base_ref} <==\n"
                            + log.read_text(errors="replace"))
            shutil.rmtree(workspace, ignore_errors=True)
