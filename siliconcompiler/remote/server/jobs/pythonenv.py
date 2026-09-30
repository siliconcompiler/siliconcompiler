'''
A job's Python packages, installed while it stages: on the host, or built into
an image a node resolved to (surface *A node's own Python packages*;
implementation-notes §L).

A part of :class:`~siliconcompiler.remote.server.jobs.service.JobService`, which composes them.
'''

import json
import os
import shutil

from typing import Any, Dict, List, Tuple

from siliconcompiler.remote import environment
from siliconcompiler.remote.server.jobs.common import (
    _Absent, _NoLongerStaging, _ServerFailure, _bounded, _build_refusal, _install_lines,
    _python_names, logger)
from siliconcompiler.remote.server.running.dispatch import DispatchError
from siliconcompiler.remote.server.software import images


class PythonEnvMixin:
    '''A job's Python packages, installed while it stages.'''

    ######################################################################
    # The job's Python packages (surface *A node's own Python packages,
    # built while staging*; implementation-notes §L)
    ######################################################################

    def _python_install(self, job, summary):
        '''What the job's Python install is: ``(packages, wheels)`` -- the
        lists less each distribution a wheel carries, which its wheel replaces,
        and the wheels' paths -- or None where there is nothing to install: no
        node runs the user's Python, or the job lists no requirement and
        uploads no wheel. Constraints alone install nothing.'''
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
        '''Host mode: the job's Python packages installed while it stages,
        into its user's cache, and linked where each node that runs the user's
        Python finds them (`Task.get_runtime_environmental_variables`). Returns
        each package no configured index has, for which the job is sent back
        -- empty once installed.

        🔴 **A package that will not install rejects the job** --
        `software-unavailable`, `reason: "uninstallable"`, naming each package
        and the target Python and platform -- before any node runs. An index
        that does not answer is this server's failure: `staging-failed`.
        '''
        from siliconcompiler.remote.server.packages import envinstall

        if self._config["containers"] or "python.env" not in (self._config["features"] or ()):
            return []
        wanted = self._python_install(job, summary)
        if wanted is None:
            return []
        packages, wheels = wanted

        self._phase(job["id"], "installing the job's Python packages")
        try:
            target, record = envinstall.install(
                packages, wheels, self.cache_dir(job["user_id"]) / "python-env", logger,
                constrain=_python_names(job),
                indexes=list(self._config["package_indexes"] or []))
        except envinstall.InstallFailed as e:
            if e.result.get("absent"):
                return list(e.result["absent"])
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

        # 🔴 Where nodes run on the host there is no image, so no
        # `resolved_versions`: the job-level `logs` is the record of what the
        # install added (profile §5; database D143), fresh or cached alike.
        self._record_in_job_log(job, _install_lines(record, "this host"))
        if self._row(job["id"])["state"] != "staging":
            raise _NoLongerStaging(job["id"])
        return []

    def _build_environments(self, job, summary, plan):
        '''``(plan, absent)``: ``plan`` with every node that runs the user's
        Python moved onto the image built for the job's packages on the image
        it resolved to -- reused where one exists for that base and key, built
        otherwise, and one build per base, shared by every such node of the job
        -- or, with ``plan`` as it was, each package no configured index has,
        for which the job is sent back.

        🔴 **A package that will not install rejects the job** from
        `staging`: `software-unavailable`, `reason: "uninstallable"`, naming
        each package and the target Python and platform.
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
                                    inputs["constraints"], digests, _python_names(job))
            if key not in done:
                try:
                    done[key] = self._derived_for(job, node, base_id, base_ref, key, inputs)
                except _Absent as e:
                    return plan, e.names
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
            self._record_in_job_log(job, _install_lines(result, base_ref))
            return image_id, images.pinned_ref(result["ref"], result["digest"])

    def _run_build(self, job, node, base_ref, key, inputs) -> Dict[str, Any]:
        '''One build, as a job of its own in the builder queue; its result, or
        the job refused with why. Raises _Absent for a package no configured
        index has.'''
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
            timeout = int(self._config["env_build_timeout_seconds"])
            (workspace / envbuild.SPEC).write_text(json.dumps({
                "key": key, "base_ref": base_ref, "base_digest": base_ref.split("@", 1)[1],
                "bundles_root": str(self.bundles_root()), "mounts": self.container_mounts(),
                "index_allowlist": list(self._config["index_allowlist"] or []),
                # Where pip looks: the deployment's, never the job's.
                "indexes": list(self._config["package_indexes"] or []),
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

            # 🔴 A cancel stops the build: the job leaving `staging` is a build
            # nobody is waiting for.
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
                log = workspace / envbuild.LOG
                tail = "\n".join(log.read_text(errors="replace").strip().splitlines()[-10:]) \
                    if log.is_file() else ""
                raise _ServerFailure(_bounded(
                    f"the build of the job's Python packages on {base_ref} did not "
                    f"finish within {timeout}s" + (f":\n{tail}" if tail else "")))
            if not result.get("ok") and result.get("reason") == "absent":
                raise _Absent(list(result.get("absent") or []))
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
            shutil.rmtree(workspace, ignore_errors=True)
