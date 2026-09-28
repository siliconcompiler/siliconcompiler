'''
One node's environment file, installed into a directory of its own.

Run by the builder inside the node's base image, and by host mode on the host
(surface D131). The same file for both, so there is one answer to *what does
installing an environment mean*.

🔴 **Standard library only, and it never imports SiliconCompiler.** In the
builder it runs under the base image's own Python, and the SiliconCompiler
there is whatever version the image holds -- this module may not exist in it.
It is copied in and run as a file.

🔴 **Against what the interpreter holds** (surface D161, build rule 5). pip runs
in a virtual environment made from the node's Python with its installed
packages visible, and a constraints file pins each distribution the job's
`requires.python` names to the version installed:

- what the interpreter has at a satisfying version is counted as installed,
  and never installed a second time -- a testbench package depending on cocotb
  does not bring a second cocotb ahead of the one the simulator loads;
- a pin needing a different version of a pinned distribution is a resolution
  failure, reported as uninstallable;
- anything else it needs a different version of lands in the environment, and
  the interpreter's own copy is left as it is.

The result is the environment's own site-packages, which holds only what was
added. ``pip install --target`` is never used: it ignores what is installed.

⚠️ ``--system-site-packages`` alone is not "its installed packages visible"
when the interpreter is itself a virtual environment -- an image with
SiliconCompiler in ``/venv`` -- because a venv made from a venv sees the BASE
installation's packages and not its parent's. So the environment also carries
a ``.pth`` that adds this interpreter's own site directories.

**Wheels only** (`--only-binary :all:`) unless ``--allow-source``: installing
from source runs the package's own code, so a source distribution is built only
in the isolated builder, whose one way out is the proxy.

**From the deployment's indexes** (``--index-url``, the primary first), never
from any configuration pip would otherwise read.

**Each line at its exact version, else within its release line** (surface *How
it is built*): where a pinned version has nothing that installs for this Python
and platform, the line is tried once more as ``X.*`` -- ``0.Y.*`` below 1.0 --
and what was installed instead is recorded under ``substituted``. Only a line
that is not found is retried: one that conflicts with a pinned distribution is
uninstallable as it stands.

Usage::

    python3 pipbuild.py --requirements R --site S --result J
                        [--constrain NAME ...] [--proxy-socket P]
                        [--index-url URL ...] [--allow-source]

``J`` is written whatever happens, as JSON: the return code, this Python's
tag, version and platform, what was installed, and, when pip failed, the
packages it named and the tail of its output.
'''

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import sysconfig
import tempfile
import threading

from importlib import metadata

_PEP440 = re.compile(
    r"^([1-9][0-9]*!)?(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))*"
    r"((a|b|rc)(0|[1-9][0-9]*))?(\.post(0|[1-9][0-9]*))?(\.dev(0|[1-9][0-9]*))?"
    r"(\+[a-z0-9]+(\.[a-z0-9]+)*)?$", re.IGNORECASE)

_NOT_FOUND = (re.compile(r"No matching distribution found for ([^\s;]+)"),
              re.compile(r"Could not find a version that satisfies the requirement "
                         r"([^\s;]+)"))
_CONFLICT = re.compile(r"The user requested \(constraint\) ([^\s;]+)|"
                       r"The user requested ([^\s;]+)")
# The .pth that makes this interpreter's packages visible in the environment.
_VISIBLE = "_sc_interpreter.pth"

# pip could not reach an index at all -- which says nothing about the pins.
_NETWORK = re.compile(r"Retrying \(Retry|ProxyError|NewConnectionError|ConnectTimeoutError|"
                      r"Max retries exceeded|Tunnel connection failed|"
                      r"Temporary failure in name resolution")


def canonical(name: str) -> str:
    '''A distribution name as PEP 503 compares it.'''
    return re.sub(r"[-_.]+", "-", name).lower()


def provided():
    '''What this interpreter already holds: canonical name -> version.

    The first of a name on ``sys.path`` wins, as it does for an import.
    '''
    found = {}
    for dist in metadata.distributions():
        name = dist.metadata["Name"]
        if name and canonical(name) not in found:
            found[canonical(name)] = dist.version
    return found


def constraints(names):
    '''``name==version`` for each of ``names`` this interpreter holds, at the
    version it holds. A name it does not hold constrains nothing; a version
    pip could not parse is left out rather than failing every build.'''
    held = provided()
    lines = []
    for name in sorted({canonical(name) for name in names}):
        version = held.get(name)
        if version and _PEP440.match(version):
            lines.append(f"{name}=={version}")
    return lines


def installed(site):
    '''The distributions ``site`` holds, as sorted ``[name, version]`` pairs.'''
    pairs = []
    for dist in metadata.distributions(path=[site]):
        name = dist.metadata["Name"]
        if name:
            pairs.append([canonical(name), dist.version])
    return sorted(pairs)


def named(output: str):
    '''The requirements pip's output says it could not satisfy.'''
    found = []
    for pattern in _NOT_FOUND:
        for match in pattern.finditer(output):
            if match.group(1) not in found:
                found.append(match.group(1))
    if not found:
        for match in _CONFLICT.finditer(output):
            requirement = match.group(1) or match.group(2)
            if requirement and requirement not in found:
                found.append(requirement)
    return found


# A requirement line as the format writes it: name[extras]==version ; marker.
_LINE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(\[[^\]]*\])?==([^\s;]+)(.*)$")


def release_line(version: str):
    '''``X.*``, or ``0.Y.*`` below 1.0, for a version; None where it has no
    plain release segment to take one from.'''
    match = re.match(r"^(\d+)(?:\.(\d+))?", version)
    if not match:
        return None
    major, minor = match.group(1), match.group(2)
    if major != "0":
        return f"{int(major)}.*"
    return f"0.{int(minor)}.*" if minor is not None else None


def _widened(requirements: str, missing):
    '''The requirements with each line pip could not find moved to its
    release line: (the new text, {name: the line's version}) -- or None where
    no line changed.'''
    wanted = {canonical(re.split(r"[\[=<>!~; ]", one, maxsplit=1)[0]) for one in missing}
    lines, widened = [], {}
    with open(requirements) as f:
        for raw in f.read().splitlines():
            match = _LINE.match(raw.strip())
            if match and canonical(match.group(1)) in wanted:
                series = release_line(match.group(3))
                if series:
                    widened[canonical(match.group(1))] = match.group(3)
                    raw = f"{match.group(1)}{match.group(2) or ''}=={series}{match.group(4)}"
            lines.append(raw)
    return ("\n".join(lines) + "\n", widened) if widened else None


def install(requirements: str, site: str, constrain=(), proxy_socket=None, echo=None,
            indexes=(), allow_source=False):
    '''Install ``requirements`` into ``site``, against this interpreter, with
    each of ``constrain`` pinned to the version it holds, from ``indexes`` --
    the primary first -- and from source only where ``allow_source``. Returns
    the result record; ``echo`` is handed pip's output, whole.'''
    import glob
    import venv

    # Beside the result, so it lands with one rename -- and so pip's downloads
    # go to disk rather than to a builder's small /tmp.
    parent = os.path.dirname(os.path.abspath(site))
    os.makedirs(parent, exist_ok=True)
    work = tempfile.mkdtemp(prefix=".sc-pip-", dir=parent)
    try:
        environment = os.path.join(work, "venv")
        venv.EnvBuilder(system_site_packages=True, with_pip=False,
                        symlinks=True).create(environment)
        # lib and lib64 where a scheme splits them -- and where lib64 is only a
        # link to lib, once.
        packages = sorted({os.path.realpath(path) for path in glob.glob(
            os.path.join(environment, "lib*", "python*", "site-packages"))})
        if not packages:
            raise RuntimeError(f"the environment at {environment} has no site-packages")
        # This interpreter's own sites, its .pth files processed: a venv made
        # from a venv sees the base installation's otherwise.
        sites = [path for path in site_directories() if os.path.isdir(path)]
        with open(os.path.join(packages[0], _VISIBLE), "w") as f:
            f.write(f"import site; [site.addsitedir(p) for p in {sites!r}]\n")

        pinned = os.path.join(work, "constraints.txt")
        with open(pinned, "w") as f:
            f.write("# What the job's requires.python pins, at the versions held here.\n")
            for line in constraints(constrain):
                f.write(f"{line}\n")

        # 🔴 No configuration of anybody's: the indexes are the deployment's,
        # passed below, and a job names none.
        env = {key: value for key, value in os.environ.items()
               if not key.upper().startswith("PIP_") and key != "PYTHONPATH"}
        env["PIP_CONFIG_FILE"] = os.devnull
        if proxy_socket:
            # 🔴 In the builder the only way out is the proxy, which admits the
            # index allowlist.
            env = {key: value for key, value in env.items()
                   if not key.upper().startswith(("HTTP_PROXY", "HTTPS_PROXY",
                                                  "ALL_PROXY", "NO_PROXY"))}
            port = _forward(proxy_socket)
            url = f"http://127.0.0.1:{port}"
            env.update({"HTTP_PROXY": url, "HTTPS_PROXY": url, "http_proxy": url,
                        "https_proxy": url, "PYTHONNOUSERSITE": "1", "HOME": work})
        env["TMPDIR"] = work

        command = [os.path.join(environment, "bin", "python"), "-m", "pip", "install",
                   "--no-input", "--disable-pip-version-check",
                   "--no-cache-dir", "--no-compile", "--no-warn-script-location",
                   "-c", pinned]
        if not allow_source:
            command += ["--only-binary", ":all:"]
        for number, index in enumerate(indexes or ()):
            command += ["--index-url" if number == 0 else "--extra-index-url", index]

        def run(listed):
            done = subprocess.run(command + ["-r", listed], env=env,
                                  stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True)
            if echo is not None:
                echo(done.stdout)
            return done

        done = run(requirements)
        substituted = {}
        if done.returncode != 0:
            missing = [one for pattern in _NOT_FOUND for one in pattern.findall(done.stdout)]
            again = _widened(requirements, missing) if missing else None
            if again is not None:
                widened = os.path.join(work, "requirements-widened.txt")
                with open(widened, "w") as f:
                    f.write(again[0])
                retried = run(widened)
                if retried.returncode == 0:
                    done, substituted = retried, again[1]

        result = {"returncode": done.returncode, "python": sys.implementation.cache_tag,
                  "version": ".".join(map(str, sys.version_info[:3])),
                  "platform": sysconfig.get_platform()}
        if done.returncode != 0:
            result["unresolved"] = named(done.stdout)
            result["network"] = bool(_NETWORK.search(done.stdout))
            result["tail"] = "\n".join(done.stdout.strip().splitlines()[-20:])
            return result

        # The environment's own site-packages -- lib and lib64 where a scheme
        # splits them -- holds only what was added.
        os.unlink(os.path.join(packages[0], _VISIBLE))
        os.makedirs(site, exist_ok=True)
        for directory in packages:
            _merge(directory, site)
        result["installed"] = installed(site)
        if substituted:
            # What ran in place of each line's own version, within its line.
            held = dict(result["installed"])
            result["substituted"] = {name: [version, held.get(name)]
                                     for name, version in sorted(substituted.items())}
        return result
    finally:
        shutil.rmtree(work, ignore_errors=True)


def site_directories():
    '''Where this interpreter's installed packages are.'''
    import site

    return list(site.getsitepackages())


def _merge(source, target):
    for entry in sorted(os.listdir(source)):
        there = os.path.join(target, entry)
        if os.path.isdir(os.path.join(source, entry)) and os.path.isdir(there):
            _merge(os.path.join(source, entry), there)
        else:
            shutil.move(os.path.join(source, entry), there)


def _forward(path):
    '''A loopback port that reaches the builder's proxy on ``path``.

    The container has a network namespace of its own with nothing but a
    loopback in it; the proxy is a unix socket bound in from the host.
    Returns the port.
    '''
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(32)

    def pipe(source, sink):
        try:
            while True:
                data = source.recv(65536)
                if not data:
                    break
                sink.sendall(data)
        except OSError:
            pass
        finally:
            for end in (source, sink):
                try:
                    end.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

    def serve():
        while True:
            client, _ = listener.accept()
            upstream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                upstream.connect(path)
            except OSError:
                client.close()
                continue
            threading.Thread(target=pipe, args=(client, upstream), daemon=True).start()
            threading.Thread(target=pipe, args=(upstream, client), daemon=True).start()

    threading.Thread(target=serve, daemon=True).start()
    return listener.getsockname()[1]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="pipbuild")
    parser.add_argument("--requirements", required=True)
    parser.add_argument("--site", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--constrain", action="append", default=[])
    parser.add_argument("--proxy-socket")
    parser.add_argument("--index-url", action="append", default=[])
    parser.add_argument("--allow-source", action="store_true")
    args = parser.parse_args(argv)

    try:
        result = install(args.requirements, args.site, constrain=args.constrain,
                         proxy_socket=args.proxy_socket, echo=sys.stdout.write,
                         indexes=args.index_url, allow_source=args.allow_source)
    except Exception as e:                                      # noqa: BLE001
        result = {"returncode": -1, "python": sys.implementation.cache_tag,
                  "platform": sysconfig.get_platform(), "unresolved": [],
                  "tail": f"{type(e).__name__}: {e}"}
    with open(args.result, "w") as f:
        json.dump(result, f)
    return 0 if result["returncode"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
