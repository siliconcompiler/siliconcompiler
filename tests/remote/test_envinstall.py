import logging
import os
import subprocess
import sys

import pytest

from siliconcompiler.remote import environment
from siliconcompiler.remote.server.packages import envinstall, pipbuild


# A job's Python packages installed on the host while it stages (host mode).
# pip is faked, and no index asked: what pip is handed, and what is left, is asserted.


LOG = logging.getLogger("test")


@pytest.fixture
def pip(monkeypatch):
    '''Every pip call, and what the files it was handed said. Installs a
    marker into the target, or fails where told to.'''
    calls = []

    def fake(command, **kwargs):
        import glob

        handed = open(command[command.index("-r") + 1]).read()
        constraints = open(command[command.index("-c") + 1]).read()
        calls.append((command, handed, constraints))
        fake.env = kwargs.get("env")
        failure = fake.fail.pop(0) if isinstance(fake.fail, list) else fake.fail
        if failure:
            return subprocess.CompletedProcess(command, 1, stdout=failure)
        # Into the environment whose Python ran it.
        environment = os.path.dirname(os.path.dirname(command[0]))
        site, = {os.path.realpath(path) for path in glob.glob(
            os.path.join(environment, "lib*", "python*", "site-packages"))}
        open(os.path.join(site, "installed.txt"), "w").write(handed)
        return subprocess.CompletedProcess(command, 0, stdout="")

    fake.fail = None
    monkeypatch.setattr(subprocess, "run", fake)
    monkeypatch.setattr(pipbuild, "on_index", lambda name, indexes, proxy=None:
                        name not in fake.absent)

    def listing(name, version, indexes, proxy=None):
        # What the index lists at exactly that version: a wheel, unless absent.
        return {"wheels": [] if name in fake.absent else [f"{name}-{version}"],
                "compiled": [], "sources": [], "yanked": []}

    monkeypatch.setattr(pipbuild, "listing", listing)
    fake.absent = set()
    fake.calls = calls
    return fake


def install(root, requirements=(), constraints=(), wheels=(), **kwargs):
    packages = environment.parse({"requirements": list(requirements),
                                  "constraints": list(constraints)})
    return envinstall.install(packages, [str(path) for path in wheels], root, LOG, **kwargs)


def test_the_lists_are_never_handed_to_pip_as_the_job_wrote_them(pip, tmp_path, monkeypatch):
    '''🔴 Rewritten from what parsed, canonical names, the wheels beside them --
    binaries only, from the deployment's indexes, and nobody's pip configuration.'''
    monkeypatch.setenv("PIP_INDEX_URL", "https://somewhere.example/simple/")
    wheel = tmp_path / "scfake_helper-0.1.0-py3-none-any.whl"
    wheel.write_bytes(b"PK")

    target, _ = install(tmp_path / "cache", ["Sc_Fake.Bits==2.0.1"], ["scfake-other==1.0"],
                        [wheel], indexes=["https://pypi.org/simple/",
                                          "https://extra.example/simple/"])

    (command, handed, constraints), = pip.calls
    assert command[1:4] == ["-m", "pip", "install"]
    assert command[command.index("--only-binary") + 1] == ":all:"
    assert command[command.index("--index-url") + 1] == "https://pypi.org/simple/"
    assert command[command.index("--extra-index-url") + 1] == "https://extra.example/simple/"
    assert command[-1] == str(wheel)
    assert "PIP_INDEX_URL" not in pip.env and pip.env["PIP_CONFIG_FILE"] == os.devnull
    assert handed == "sc-fake-bits==2.0.1\n"
    assert constraints.splitlines()[-1] == "scfake-other==1.0"
    assert os.path.isfile(os.path.join(target, "installed.txt"))


def test_what_this_host_holds_is_pinned_and_wins(pip, tmp_path):
    '''🔴 A venv seeing this Python's packages, all pinned -- never `--target`,
    which ignores them; a listed version of one it holds is ignored, and said.'''
    from importlib import metadata

    held = metadata.version("pytest")
    _, record = install(tmp_path, ["scfake-bits==2.0.1", "pytest==0.0.1"], ["packaging==0.0.2"])

    (command, handed, constraints), = pip.calls
    assert "--target" not in command
    assert f"pytest=={held}" in constraints.splitlines()
    assert "pytest==0.0.1" not in handed and "packaging==0.0.2" not in constraints
    assert record["ignored"] == {"pytest": ["0.0.1", held],
                                 "packaging": ["0.0.2", metadata.version("packaging")]}


def test_the_same_set_is_built_once_and_shared_and_reports_what_it_added(
        pip, tmp_path, monkeypatch):
    '''Keyed by lists, wheel digests, indexes and this Python. 🔴 A cached one
    reports what the fresh one added: the job log is the only record (§5).'''
    monkeypatch.setattr(pipbuild, "installed", lambda site: [["scfake-bits", "2.0.1"]])
    wheel = tmp_path / "scfake_helper-0.1.0-py3-none-any.whl"
    wheel.write_bytes(b"PK one")

    first, fresh = install(tmp_path, ["scfake-bits==2.0.1"])
    again, cached = install(tmp_path, ["scfake-bits==2.0.1"])
    other, _ = install(tmp_path, ["scfake-bits==2.0.2"])
    carried, _ = install(tmp_path, ["scfake-bits==2.0.1"], wheels=[wheel])
    wheel.write_bytes(b"PK two")
    changed, _ = install(tmp_path, ["scfake-bits==2.0.1"], wheels=[wheel])

    assert first == again
    assert len({first, other, carried, changed}) == 4
    assert len(pip.calls) == 4
    assert fresh == cached == {"installed": [["scfake-bits", "2.0.1"]], "substituted": {},
                               "ignored": {}, "yanked": []}


@pytest.mark.parametrize("output", [
    "ERROR: no wheel for x",
    "The user requested (constraint) cocotb==2.1.0",    # against a pin: its line not widened
])
def test_one_that_will_not_install_says_which_and_leaves_nothing(pip, tmp_path, output):
    pip.fail = output

    with pytest.raises(envinstall.InstallFailed) as raised:
        install(tmp_path, ["cocotb-bus==0.2.1"])

    assert sys.implementation.cache_tag in str(raised.value) and output in str(raised.value)
    assert len(pip.calls) == 1
    assert not [path for path in tmp_path.iterdir() if not path.name.endswith(".lock")]


def test_a_version_that_does_not_install_is_tried_within_its_release_line(
        pip, tmp_path, monkeypatch):
    '''§L: else its release line -- `X.*`, or `0.Y.*` below 1.0 -- one entry
    relaxed at a time, and the substitution recorded.'''
    pip.fail = ["ERROR: No matching distribution found for scfake-bits==1.26.4",
                "ERROR: No matching distribution found for scfake-tq==0.4.1", None]
    monkeypatch.setattr(pipbuild, "installed",
                        lambda site: [["scfake-bits", "1.26.9"], ["scfake-tq", "0.4.7"]])

    _, record = install(tmp_path, ["scfake-bits==1.26.4", "scfake-tq==0.4.1",
                                   "scfake-six==1.16.0"])

    (_, first, _), (_, second, _), (_, third, _) = pip.calls
    assert "scfake-bits==1.26.4" in first.splitlines()
    assert {"scfake-bits==1.*", "scfake-tq==0.4.1"} <= set(second.splitlines())
    assert {"scfake-bits==1.*", "scfake-tq==0.4.*", "scfake-six==1.16.0"} <= \
        set(third.splitlines())
    assert record["substituted"] == {"scfake-bits": ["1.26.4", "1.26.9"],
                                     "scfake-tq": ["0.4.1", "0.4.7"]}


def test_a_constraint_that_does_not_install_is_relaxed_the_same_way(pip, tmp_path):
    pip.fail = ["ERROR: Could not find a version that satisfies the requirement "
                "scfake-dep==2.3.1 (from scfake-bits)", None]

    install(tmp_path, ["scfake-bits==1.0"], ["scfake-dep==2.3.1"])

    (_, _, first), (_, _, second) = pip.calls
    assert first.splitlines()[-1] == "scfake-dep==2.3.1"
    assert second.splitlines()[-1] == "scfake-dep==2.*"


def test_a_package_no_index_has_is_absent_and_named(pip, tmp_path):
    '''What sends the job back for its wheel -- never relaxed, since no line
    of it is there.'''
    pip.absent = {"scfake-private"}
    pip.fail = ["ERROR: No matching distribution found for scfake-private==1.2.0"] * 3

    with pytest.raises(envinstall.InstallFailed) as raised:
        install(tmp_path, ["scfake-bits==1.0", "scfake-private==1.2.0"],
                indexes=["https://pypi.org/simple/"])

    assert raised.value.result["absent"] == ["scfake-private"]
    assert "scfake-private" not in pip.calls[-1][1]


def test_an_index_that_cannot_be_asked_is_the_servers_failure(pip, tmp_path, monkeypatch):
    monkeypatch.setattr(pipbuild, "on_index", lambda name, indexes, proxy=None: None)
    monkeypatch.setattr(pipbuild, "listing", lambda name, version, indexes, proxy=None: None)
    pip.fail = "ERROR: No matching distribution found for scfake-bits==1.0"

    with pytest.raises(envinstall.InstallFailed) as raised:
        install(tmp_path, ["scfake-bits==1.0"])

    assert raised.value.result["network"] is True
    assert not raised.value.result.get("absent")


def test_nothing_to_add_runs_no_pip_and_is_still_an_environment(pip, tmp_path):
    '''Every requirement one this Python holds: nothing to install, and the
    listed versions it holds another of recorded.'''
    target, record = install(tmp_path, ["pytest==0.0.1"])

    assert pip.calls == []
    assert os.path.isdir(target)
    assert list(record["ignored"]) == ["pytest"]


def test_two_jobs_at_once_never_share_an_environment_or_a_cache(pip, tmp_path, monkeypatch):
    '''🔴 Two staging threads, which the file lock does not separate: one set
    is built once and reused, two install at once, each with its own pip cache.'''
    import collections
    import threading
    import time

    fake = subprocess.run

    def slow(command, **kwargs):
        time.sleep(0.3)
        return fake(command, **kwargs)

    monkeypatch.setattr(subprocess, "run", slow)
    got, failed = [], []

    def stage(pins):
        try:
            got.append(install(tmp_path, pins)[0])
        except Exception as e:                                  # noqa: BLE001
            failed.append(e)

    threads = [threading.Thread(target=stage, args=(pins,)) for pins in
               (["scfake-bits==1.0"], ["scfake-bits==1.0"], ["scfake-other==2.0"])]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert failed == []
    assert sorted(collections.Counter(got).values()) == [1, 2]
    assert len(pip.calls) == 2
    caches = {command[command.index("--cache-dir") + 1] for command, _, _ in pip.calls}
    assert len(caches) == 2
