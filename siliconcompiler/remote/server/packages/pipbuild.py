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
in the isolated builder, whose one way out is the proxy, and only where the
operator turned source builds on.

**From the deployment's indexes** (``--index-url``, the primary first), never
from any configuration pip would otherwise read: ``--isolated``, and a cache of
the install's own.

**Each entry at its exact version, else within its release line** (§L's
order): where an index lists the version and nothing of it installs for this
Python and platform, that one entry is tried again as ``X.*`` -- ``0.Y.*``
below 1.0 -- and resolved again, and what was installed instead is recorded
under ``substituted``. **A version no configured index lists** is recorded
under ``absent`` rather than relaxed, however many other versions of the name
an index holds: the job is sent back for its wheel. **A yanked release** is
never installed, and takes its line's fallback, recorded under ``yanked`` too.
**Only a source distribution for the target**, with source builds off, is
sent back for as ``source_only`` where nothing shows it compiled, and is
uninstallable -- ``only_source`` -- where the index has a platform's wheel of
it. One that conflicts with a pinned distribution is uninstallable as it
stands.

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


def _opener(proxy):
    import urllib.request

    return urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": proxy, "https": proxy} if proxy else {}))


def _page(index, name, proxy):
    '''One index's project page for ``name`` (PEP 503), as ``(files, ok)``:
    each file it lists as ``(filename, yanked)``, and False where the index
    could not be asked. A page it does not have lists nothing.

    PEP 691's JSON where the index serves it, PEP 503's HTML otherwise, with
    PEP 592's ``data-yanked`` read from either. A ``file:`` index is a
    directory, read through its ``index.html`` as pip reads it, or listed
    where it has none -- which marks nothing yanked.'''
    import html.parser
    import urllib.error
    import urllib.request
    from urllib.parse import unquote, urlsplit

    url = f"{index.rstrip('/')}/{canonical(name)}/"
    if url.startswith("file:"):
        where = urllib.request.url2pathname(urlsplit(url).path)
        if not os.path.isdir(where):
            return [], True
        page = os.path.join(where, "index.html")
        if not os.path.isfile(page):
            return [(entry, False) for entry in sorted(os.listdir(where))
                    if os.path.isfile(os.path.join(where, entry))], True
        try:
            with open(page, encoding="utf-8", errors="replace") as f:
                kind, body = "text/html", f.read()
        except OSError:
            return [], False
    else:
        request = urllib.request.Request(url, headers={
            "Accept": "application/vnd.pypi.simple.v1+json, text/html;q=0.1"})
        try:
            with _opener(proxy).open(request, timeout=30) as answer:
                kind = answer.headers.get("Content-Type", "")
                body = answer.read(64 * 1024 * 1024).decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                return [], True
            return [], False
        except (urllib.error.URLError, OSError, ValueError):
            return [], False

    if "json" in kind:
        try:
            listed = json.loads(body).get("files") or []
        except ValueError:
            return [], False
        return [(entry.get("filename") or "", bool(entry.get("yanked")))
                for entry in listed if isinstance(entry, dict)], True

    class _Anchors(html.parser.HTMLParser):
        def __init__(self):
            super().__init__()
            self.found, self._yanked, self._in = [], False, False

        def handle_starttag(self, tag, attrs):
            if tag == "a":
                self._in, self._text = True, ""
                self._yanked = any(key == "data-yanked" for key, _ in attrs)
                self._href = dict(attrs).get("href") or ""

        def handle_data(self, data):
            if self._in:
                self._text += data

        def handle_endtag(self, tag):
            if tag == "a" and self._in:
                self._in = False
                named = self._text.strip() or unquote(
                    urlsplit(self._href).path.rsplit("/", 1)[-1])
                self.found.append((named, self._yanked))

    anchors = _Anchors()
    anchors.feed(body)
    return anchors.found, True


def _version_key(version: str):
    '''A version as PEP 440 compares release segments: `1.0` is `1.0.0`.'''
    text = (version or "").strip().lower()
    match = re.match(r"^v?(\d+(?:\.\d+)*)(.*)$", text)
    if not match:
        return (text,)
    release = [int(part) for part in match.group(1).split(".")]
    while len(release) > 1 and release[-1] == 0:
        release.pop()
    return (tuple(release), re.sub(r"[-_]", ".", match.group(2)))


# A source distribution's file name: `<name>-<version>.<one of these>`.
_SOURCES = (".tar.gz", ".zip", ".tar.bz2", ".tar.xz", ".tgz")


def _file_of(filename: str, name: str, version: str):
    '''``"wheel"``, ``"compiled"`` or ``"source"`` where ``filename`` is a
    file of ``name`` at exactly ``version``; None otherwise.'''
    lowered = filename.lower()
    if lowered.endswith(".whl"):
        parts = filename[:-4].split("-")
        if len(parts) < 5 or canonical(parts[0]) != canonical(name) or \
                _version_key(parts[1]) != _version_key(version):
            return None
        pure = parts[-2] == "none" and parts[-1] == "any"
        return "wheel" if pure else "compiled"
    for suffix in _SOURCES:
        if lowered.endswith(suffix):
            stem = filename[:-len(suffix)]
            project, _, found = stem.rpartition("-")
            if canonical(project) == canonical(name) and \
                    _version_key(found) == _version_key(version):
                return "source"
    return None


def listing(name, version, indexes, proxy=None):
    '''What the configured indexes list of ``name`` at exactly ``version``:
    ``{"wheels", "compiled", "sources", "yanked"}``, file names each, or None
    where an index could not be asked.

    🔴 **Exact-version matching** (surface D292): a version no index lists is
    absent however many other versions of that name it holds, so an unrelated
    project that happens to share the name is never installed in its place.
    A yanked file is listed as yanked only (PEP 592), and never installed.'''
    found = {"wheels": [], "compiled": [], "sources": [], "yanked": []}
    for index in indexes or ():
        files, ok = _page(index, name, proxy)
        if not ok:
            return None
        for filename, yanked in files:
            kind = _file_of(filename, name, version)
            if kind is None:
                continue
            if yanked:
                found["yanked"].append(filename)
            else:
                found[{"wheel": "wheels", "compiled": "compiled",
                       "source": "sources"}[kind]].append(filename)
    return found


def on_index(name, indexes, proxy=None):
    '''Whether any of ``indexes`` lists ``name`` at all (PEP 503): True,
    False, or None where one could not be asked. For a dependency nothing
    pinned, whose version is pip's to choose.'''
    for index in indexes or ():
        files, ok = _page(index, name, proxy)
        if not ok:
            return None
        if files:
            return True
    return False


def install(requirements, constraints, site, wheels=(), proxy_socket=None, echo=None,
            indexes=(), allow_source=False, probe=None, timeout=None):
    '''Install ``requirements`` and ``wheels`` into ``site``, under
    ``constraints``, against this interpreter, from ``indexes`` -- the primary
    first -- and from source only where ``allow_source``. Returns the result
    record; ``echo`` is handed pip's output, whole. ``probe`` answers
    :func:`listing` -- ``(name, version)`` -- for tests. ``timeout`` bounds the
    whole install, every pip run within it; past it the record says
    ``timed_out``.'''
    import glob
    import time
    import venv

    ends = None if timeout is None else time.monotonic() + timeout

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

        # 🔴 `--isolated`, and the indexes named here: neither the image's pip
        # configuration nor the environment can change where packages come
        # from. A cache of this install's own, inside its work directory, so no
        # two installs ever write one.
        command = [os.path.join(environment, "bin", "python"), "-m", "pip", "install",
                   "--isolated", "--no-input", "--disable-pip-version-check",
                   "--cache-dir", os.path.join(work, "pip-cache"),
                   "--no-compile", "--no-warn-script-location"]
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
            left = None if ends is None else max(1, ends - time.monotonic())
            try:
                done = subprocess.run(command + ["-c", limited, "-r", listed, *wheels],
                                      env=env, stdin=subprocess.DEVNULL,
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                      text=True, timeout=left)
            except subprocess.TimeoutExpired as e:
                said = e.output or ""
                if isinstance(said, bytes):
                    said = said.decode(errors="replace")
                raise _OutOfTime(said) from None
            if echo is not None:
                echo(done.stdout)
            return done

        def entry(key):
            for field in ("requirements", "constraints"):
                for one in lists[field]:
                    if one[0] == key:
                        return field, one
            return None, None

        look = probe or (lambda name, version: listing(name, version, indexes, proxy))
        found_at: dict = {}

        def listed(key, version):
            if (key, version) not in found_at:
                found_at[(key, version)] = look(key, version)
            return found_at[(key, version)]

        relaxed, absent, source_only, compiled_only, yanked = {}, [], [], [], []

        def relax(one) -> bool:
            '''One entry, to its release line: once, and only where it has one.'''
            series = release_line(one[1])
            if one[0] in relaxed or not series:
                return False
            relaxed[one[0]] = one[1]
            one[1] = series
            return True

        def cannot_ask(key):
            # An index that could not be asked says nothing about the package:
            # this server's failure, not the job's.
            result.update({"returncode": -1, "network": True, "unresolved": [],
                           "tail": f"an index could not be asked about {key}"})
            return result

        # 🔴 **Each listed entry looked up before pip runs** (surface D292): a
        # requirement at a version no index lists is absent, whatever other
        # versions of the name it holds, and goes back for its wheel -- never
        # substituted; and a yanked release, which pip would install when
        # pinned with ==, falls back to its release line instead (PEP 592). A
        # constraint is only held back from yanked here: whether one no index
        # lists matters is up to what the install needs.
        if indexes:
            for field in ("requirements", "constraints"):
                for one in list(lists[field]):
                    found = listed(one[0], one[1])
                    if found is None:
                        return cannot_ask(one[0])
                    if field == "requirements" and not any(found.values()):
                        absent.append(one[0])
                        lists[field].remove(one)
                    elif found["yanked"] and not (found["wheels"] or found["compiled"]
                                                  or found["sources"]):
                        if relax(one):
                            yanked.append(one[0])

        # Each round changes one entry, and each entry changes at most twice:
        # relaxed once, then sent back or given up on once.
        rounds = 2 * (len(lists["requirements"]) + len(lists["constraints"])) + 2
        done = None
        if lists["requirements"] or wheels:
            try:
                done = run()
            except _OutOfTime as e:
                return _timed_out(result, e, echo)
        while done is not None and done.returncode != 0 and rounds > 0:
            rounds -= 1
            if _NETWORK.search(done.stdout):
                break
            changed = False
            for key in [_name_of(one) for pattern in _NOT_FOUND
                        for one in pattern.findall(done.stdout)]:
                if key in absent or key in source_only or key in compiled_only:
                    continue
                field, one = entry(key)
                if one is None:
                    # A dependency nothing pinned, pip's to choose: absent
                    # where no index lists it at all -- image-only mode asks
                    # for a wheel's own dependencies this way, a second trip.
                    there = on_index(key, indexes, proxy)
                    if there is None:
                        return cannot_ask(key)
                    if not there:
                        absent.append(key)
                        changed = True
                        break
                    continue
                found = listed(key, relaxed.get(key, one[1]))
                if found is None:
                    return cannot_ask(key)
                if not any(found.values()):
                    absent.append(key)
                    lists[field].remove(one)
                    changed = True
                    break
                # Listed at that version, and nothing of it installs for this
                # Python and platform: its release line, once.
                if relax(one):
                    changed = True
                    break
                if found["sources"] and not (found["wheels"] or allow_source):
                    # 🔴 Only a source distribution for this target, and no
                    # source builds. A version with a platform's wheel is
                    # compiled, and no wheel of the client's could run here;
                    # otherwise the client's wheel of its installed copy
                    # answers it, sent back for as a package no index has.
                    if found["compiled"]:
                        compiled_only.append(key)
                    else:
                        source_only.append(key)
                        lists[field].remove(one)
                        changed = True
                        break
            if not changed:
                break
            if not lists["requirements"] and not wheels:
                done = None
                break
            try:
                done = run()
            except _OutOfTime as e:
                return _timed_out(result, e, echo)

        if yanked:
            result["yanked"] = sorted(yanked)
        if absent or source_only:
            # 🔴 Sent back for its wheel, whatever else installed: what the
            # install becomes once it arrives is decided then.
            result.update({"returncode": 1, "absent": sorted(absent),
                           "source_only": sorted(source_only), "unresolved": [],
                           "tail": "\n".join((done.stdout if done else "").strip()
                                             .splitlines()[-20:])})
            return result
        if done is not None and done.returncode != 0:
            result.update({"returncode": done.returncode, "unresolved": named(done.stdout),
                           "network": bool(_NETWORK.search(done.stdout)),
                           "only_source": sorted(compiled_only),
                           "tail": "\n".join(done.stdout.strip().splitlines()[-20:])})
            return result
        if done is None:
            # Nothing was left to install: the interpreter holds it all.
            os.makedirs(site, exist_ok=True)
            result["installed"] = []
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


class _OutOfTime(Exception):
    '''A pip run past what was left of the install's time; its output so far.'''


def _timed_out(result, error, echo):
    '''The record of an install that ran out of time.'''
    said = str(error)
    if echo is not None:
        echo(said)
    result.update({"returncode": -1, "timed_out": True, "unresolved": [],
                   "tail": "\n".join(said.strip().splitlines()[-20:])})
    return result


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
