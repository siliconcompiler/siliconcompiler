'''
A job's Python packages, installed into a directory of their own.

Run by the builder inside the node's base image, and by host mode on the host
(surface *How it is built, while the job is staging*; implementation-notes
§L). The same file for both, so there is one answer to *what does installing
a job's packages mean*.

🔴 **Standard library only, and it never imports SiliconCompiler.** In the
builder it runs under the base image's own Python, and the SiliconCompiler
there is whatever version the image holds -- this module may not exist in it.
It is copied in and run as a file.

🔴 **Against what the interpreter holds.** pip runs in a virtual environment
made from the node's Python with its installed packages visible, and every
distribution the interpreter holds is pinned, in the constraints, to the
version it holds -- which wins over the job's own lists:

- a listed distribution the interpreter holds stays at its version, is never
  installed a second time, and its listed version is recorded as ignored --
  a testbench package depending on cocotb does not bring a second cocotb
  ahead of the one the simulator loads;
- a requirement needing a different version of one it holds is a resolution
  failure, reported as uninstallable;
- nothing the interpreter holds is ever changed.

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

**Each entry at its exact version, else within its release line** (§L's
order): where a listed version has nothing that installs for this Python and
platform, that one entry is tried again as ``X.*`` -- ``0.Y.*`` below 1.0 --
and resolved again, and what was installed instead is recorded under
``substituted``. **A package no configured index has at all** is recorded
under ``absent`` rather than relaxed: the job is sent back for its wheel. One
that conflicts with a pinned distribution is uninstallable as it stands.

Usage::

    python3 pipbuild.py --requirements R --constraints C [--wheel W ...]
                        --site S --result J [--proxy-socket P]
                        [--index-url URL ...] [--allow-source]

``R`` and ``C`` are files of ``name==version`` lines the server wrote. ``J`` is
written whatever happens, as JSON: the return code, this Python's tag, version
and platform, what was installed, substituted, ignored and absent, and, when
pip failed, the packages it named and the tail of its output.
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


def pins(held=None):
    '''``name==version`` for every distribution this interpreter holds, at the
    version it holds: what the constraints pin, so none is installed a second
    time. A version pip could not parse is left out rather than failing every
    build.'''
    held = provided() if held is None else held
    return [f"{name}=={version}" for name, version in sorted(held.items())
            if version and _PEP440.match(version)]


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


def _name_of(requirement: str) -> str:
    return canonical(re.split(r"[\[=<>!~;( ]", requirement.strip(), maxsplit=1)[0])


# An entry as the server writes it: name==version.
_LINE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==(\S+)$")


def read_entries(path):
    '''The ``[name, version]`` entries of a file the server wrote, comments
    and blank lines left out.'''
    entries = []
    if not path:
        return entries
    with open(path) as f:
        for raw in f.read().splitlines():
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            match = _LINE.match(line)
            if not match:
                raise ValueError(f"{path}: {line!r} is not name==version")
            entries.append([match.group(1), match.group(2)])
    return entries


def wheel_name(path):
    '''The canonical distribution a wheel's file name says it is.'''
    return canonical(os.path.basename(path).split("-", 1)[0])


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


def on_index(name, indexes, proxy=None):
    '''Whether any of ``indexes`` has a project page for ``name`` at all
    (PEP 503): True, False, or None where one could not be asked.

    What tells *a package no index has* -- the job is sent back for its wheel
    -- from *one no version of which installs here*, which pip's own output
    says the same way.'''
    import urllib.error
    import urllib.request
    from urllib.parse import urlsplit

    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": proxy, "https": proxy} if proxy else {}))
    for index in indexes or ():
        url = f"{index.rstrip('/')}/{canonical(name)}/"
        if url.startswith("file:"):
            if os.path.isdir(urllib.request.url2pathname(urlsplit(url).path)):
                return True
            continue
        request = urllib.request.Request(url, headers={
            "Accept": "application/vnd.pypi.simple.v1+json, text/html;q=0.1"})
        try:
            with opener.open(request, timeout=30) as answer:
                if answer.status == 200:
                    return True
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                continue
            return None
        except (urllib.error.URLError, OSError, ValueError):
            return None
    return False


def install(requirements, constraints, site, wheels=(), proxy_socket=None, echo=None,
            indexes=(), allow_source=False, probe=None):
    '''Install ``requirements`` and ``wheels`` into ``site``, under
    ``constraints``, against this interpreter, from ``indexes`` -- the primary
    first -- and from source only where ``allow_source``. Returns the result
    record; ``echo`` is handed pip's output, whole. ``probe`` answers
    :func:`on_index`, for tests.'''
    import glob
    import venv

    held = provided()
    wheel_names = {wheel_name(path) for path in wheels}

    # 🔴 What this interpreter holds wins: it stays at its version, is never
    # installed again, and a listed version that differs is recorded.
    ignored = {}
    lists = {"requirements": [], "constraints": []}
    for field, path in (("requirements", requirements), ("constraints", constraints)):
        for name, version in read_entries(path):
            key = canonical(name)
            if key in wheel_names:
                continue
            if key in held:
                if held[key] != version:
                    ignored[key] = [version, held[key]]
                continue
            lists[field].append([key, version])

    result = {"returncode": 0, "python": sys.implementation.cache_tag,
              "version": ".".join(map(str, sys.version_info[:3])),
              "platform": sysconfig.get_platform(), "installed": [],
              "ignored": ignored}
    if not lists["requirements"] and not wheels:
        # Nothing to add: the interpreter holds it all.
        os.makedirs(site, exist_ok=True)
        return result

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

        # 🔴 No configuration of anybody's: the indexes are the deployment's,
        # passed below, and a job names none.
        env = {key: value for key, value in os.environ.items()
               if not key.upper().startswith("PIP_") and key != "PYTHONPATH"}
        env["PIP_CONFIG_FILE"] = os.devnull
        proxy = None
        if proxy_socket:
            # 🔴 In the builder the only way out is the proxy, which admits the
            # index allowlist.
            env = {key: value for key, value in env.items()
                   if not key.upper().startswith(("HTTP_PROXY", "HTTPS_PROXY",
                                                  "ALL_PROXY", "NO_PROXY"))}
            port = _forward(proxy_socket)
            proxy = f"http://127.0.0.1:{port}"
            env.update({"HTTP_PROXY": proxy, "HTTPS_PROXY": proxy, "http_proxy": proxy,
                        "https_proxy": proxy, "PYTHONNOUSERSITE": "1", "HOME": work})
        env["TMPDIR"] = work

        command = [os.path.join(environment, "bin", "python"), "-m", "pip", "install",
                   "--no-input", "--disable-pip-version-check",
                   "--no-cache-dir", "--no-compile", "--no-warn-script-location"]
        if not allow_source:
            command += ["--only-binary", ":all:"]
        if not indexes:
            command.append("--no-index")
        for number, index in enumerate(indexes or ()):
            command += ["--index-url" if number == 0 else "--extra-index-url", index]

        held_pins = pins(held)

        def run():
            listed = os.path.join(work, "requirements.txt")
            limited = os.path.join(work, "constraints.txt")
            with open(listed, "w") as f:
                f.write("".join(f"{name}=={version}\n"
                                for name, version in lists["requirements"]))
            with open(limited, "w") as f:
                f.write("# What this interpreter holds, at the versions it holds.\n")
                f.write("".join(f"{line}\n" for line in held_pins))
                f.write("".join(f"{name}=={version}\n"
                                for name, version in lists["constraints"]))
            done = subprocess.run(command + ["-c", limited, "-r", listed, *wheels], env=env,
                                  stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True)
            if echo is not None:
                echo(done.stdout)
            return done

        def entry(key):
            for field in ("requirements", "constraints"):
                for one in lists[field]:
                    if one[0] == key:
                        return field, one
            return None, None

        asked = probe or (lambda name: on_index(name, indexes, proxy))
        relaxed, absent = {}, []
        # Each round changes one entry, and each entry changes at most twice:
        # relaxed once, or found absent once.
        rounds = 2 * (len(lists["requirements"]) + len(lists["constraints"])) + 2
        done = run()
        while done.returncode != 0 and rounds > 0:
            rounds -= 1
            if _NETWORK.search(done.stdout):
                break
            changed = False
            for key in [_name_of(one) for pattern in _NOT_FOUND
                        for one in pattern.findall(done.stdout)]:
                if key in absent:
                    continue
                field, one = entry(key)
                there = asked(key)
                if there is None:
                    # An index that could not be asked says nothing about
                    # the package: this server's failure, not the job's.
                    result["network"] = True
                    break
                if not there:
                    absent.append(key)
                    if one is not None:
                        lists[field].remove(one)
                    changed = True
                    break
                series = release_line(one[1]) if one is not None and key not in relaxed \
                    else None
                if series:
                    relaxed[key] = one[1]
                    one[1] = series
                    changed = True
                    break
            if not changed or result.get("network"):
                break
            if not lists["requirements"] and not wheels:
                break
            done = run()

        if absent:
            # 🔴 Sent back for its wheel, whatever else installed: what the
            # install becomes once it arrives is decided then.
            result.update({"returncode": 1, "absent": sorted(absent), "unresolved": [],
                           "tail": "\n".join(done.stdout.strip().splitlines()[-20:])})
            return result
        if done.returncode != 0:
            result.update({"returncode": done.returncode, "unresolved": named(done.stdout),
                           "network": bool(result.get("network")
                                           or _NETWORK.search(done.stdout)),
                           "tail": "\n".join(done.stdout.strip().splitlines()[-20:])})
            return result

        # The environment's own site-packages -- lib and lib64 where a scheme
        # splits them -- holds only what was added.
        os.unlink(os.path.join(packages[0], _VISIBLE))
        os.makedirs(site, exist_ok=True)
        for directory in packages:
            _merge(directory, site)
        result["installed"] = installed(site)
        if relaxed:
            # What ran in place of each entry's own version, within its line.
            got = dict(result["installed"])
            result["substituted"] = {name: [version, got.get(name)]
                                     for name, version in sorted(relaxed.items())}
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
    parser.add_argument("--constraints")
    parser.add_argument("--wheel", action="append", default=[])
    parser.add_argument("--site", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--proxy-socket")
    parser.add_argument("--index-url", action="append", default=[])
    parser.add_argument("--allow-source", action="store_true")
    args = parser.parse_args(argv)

    try:
        result = install(args.requirements, args.constraints, args.site, wheels=args.wheel,
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
