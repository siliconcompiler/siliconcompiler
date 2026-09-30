import json
import logging
import os
import subprocess
import sys

import pytest

from siliconcompiler.remote import environment
from siliconcompiler.remote.server.packages import envinstall, pipbuild


# A job's Python packages installed on the host while the job stages, into the
# user's own cache (host mode). pip is faked: what is asserted is what it is
# handed, and what is left behind. Whether an index has a package is answered
# here, never by asking one.


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
        # What the index lists at exactly that version: a wheel, unless told
        # it lists nothing, only a yanked file, or only a source.
        if name in fake.absent:
            return {"wheels": [], "compiled": [], "sources": [], "yanked": []}
        kind = fake.listed.get(name, "wheels")
        found = {"wheels": [], "compiled": [], "sources": [], "yanked": []}
        found[kind].append(f"{name}-{version}")
        if kind == "sources" and name in fake.compiled:
            found["compiled"].append(f"{name}-{version}-cp312-linux")
        return found

    monkeypatch.setattr(pipbuild, "listing", listing)
    fake.absent = set()
    fake.listed = {}
    fake.compiled = set()
    fake.calls = calls
    return fake


def packages(requirements=(), constraints=()):
    return environment.parse({"requirements": list(requirements),
                              "constraints": list(constraints)})


def test_the_lists_are_never_handed_to_pip_as_the_job_wrote_them(pip, tmp_path, monkeypatch):
    '''🔴 Written again from what parsed, one canonical name per line --
    wheels only, from the deployment's indexes, and no pip configuration of
    anybody's.'''
    monkeypatch.setenv("PIP_INDEX_URL", "https://somewhere.example/simple/")

    target, _ = envinstall.install(packages(["Sc_Fake.Bits==2.0.1"], ["scfake-other==1.0"]),
                                   [], tmp_path / "cache", LOG,
                                   indexes=["https://pypi.org/simple/",
                                            "https://extra.example/simple/"])

    (command, handed, constraints), = pip.calls
    assert command[1:4] == ["-m", "pip", "install"]
    assert "--only-binary" in command and command[command.index("--only-binary") + 1] == ":all:"
    assert command[command.index("--index-url") + 1] == "https://pypi.org/simple/"
    assert command[command.index("--extra-index-url") + 1] == "https://extra.example/simple/"
    assert "PIP_INDEX_URL" not in pip.env and pip.env["PIP_CONFIG_FILE"] == os.devnull
    assert handed == "sc-fake-bits==2.0.1\n"
    assert constraints.splitlines()[-1] == "scfake-other==1.0"
    assert os.path.isfile(os.path.join(target, "installed.txt"))


def test_what_this_host_holds_is_pinned_and_wins(pip, tmp_path):
    '''🔴 A venv that sees this Python's packages, with every one it holds
    pinned -- never `--target`, which ignores what is installed. A listed
    version of one it holds is ignored, and recorded.'''
    from importlib import metadata

    held = metadata.version("pytest")
    _, record = envinstall.install(packages(["scfake-bits==2.0.1", "pytest==0.0.1"],
                                            ["packaging==0.0.2"]), [], tmp_path, LOG)

    (command, handed, constraints), = pip.calls
    assert "--target" not in command
    assert f"pytest=={held}" in constraints.splitlines()
    assert "pytest==0.0.1" not in handed and "packaging==0.0.2" not in constraints
    assert record["ignored"] == {"pytest": ["0.0.1", held],
                                 "packaging": ["0.0.2", metadata.version("packaging")]}


def test_the_uploaded_wheels_go_in_with_the_lists_and_replace_their_entries(pip, tmp_path):
    wheel = tmp_path / "scfake_helper-0.1.0-py3-none-any.whl"
    wheel.write_bytes(b"PK")

    envinstall.install(packages(["scfake-bits==2.0.1"]), [str(wheel)], tmp_path / "c", LOG)

    (command, _, _), = pip.calls
    assert command[-1] == str(wheel)


def test_the_same_set_is_built_once_and_shared(pip, tmp_path):
    '''Keyed by the lists, the wheels' digests, the indexes and what this
    Python holds.'''
    wheel = tmp_path / "scfake_helper-0.1.0-py3-none-any.whl"
    wheel.write_bytes(b"PK one")

    first, _ = envinstall.install(packages(["scfake-bits==2.0.1"]), [], tmp_path, LOG)
    again, _ = envinstall.install(packages(["scfake-bits==2.0.1"]), [], tmp_path, LOG)
    other, _ = envinstall.install(packages(["scfake-bits==2.0.2"]), [], tmp_path, LOG)
    carried, _ = envinstall.install(packages(["scfake-bits==2.0.1"]), [str(wheel)],
                                    tmp_path, LOG)
    wheel.write_bytes(b"PK two")
    changed, _ = envinstall.install(packages(["scfake-bits==2.0.1"]), [str(wheel)],
                                    tmp_path, LOG)

    assert first == again
    assert len({first, other, carried, changed}) == 4
    assert len(pip.calls) == 4


def test_one_that_will_not_install_says_which_and_leaves_nothing(pip, tmp_path):
    pip.fail = "ERROR: no wheel for x"

    with pytest.raises(envinstall.InstallFailed) as raised:
        envinstall.install(packages(["scfake-bits==2.0.1"]), [], tmp_path, LOG)

    assert sys.implementation.cache_tag in str(raised.value)
    assert "no wheel" in str(raised.value)
    assert not [path for path in tmp_path.iterdir() if not path.name.endswith(".lock")]


def test_a_version_that_does_not_install_is_tried_within_its_release_line(
        pip, tmp_path, monkeypatch):
    '''§L's order: the exact version, else one from its release line --
    `X.*`, or `0.Y.*` below 1.0 -- one entry relaxed at a time, resolved
    again, and the substitution recorded.'''
    pip.fail = ["ERROR: No matching distribution found for scfake-bits==1.26.4",
                "ERROR: No matching distribution found for scfake-tq==0.4.1", None]
    monkeypatch.setattr(pipbuild, "installed",
                        lambda site: [["scfake-bits", "1.26.9"], ["scfake-tq", "0.4.7"]])

    _, record = envinstall.install(
        packages(["scfake-bits==1.26.4", "scfake-tq==0.4.1", "scfake-six==1.16.0"]),
        [], tmp_path, LOG)

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

    envinstall.install(packages(["scfake-bits==1.0"], ["scfake-dep==2.3.1"]), [], tmp_path, LOG)

    (_, _, first), (_, _, second) = pip.calls
    assert first.splitlines()[-1] == "scfake-dep==2.3.1"
    assert second.splitlines()[-1] == "scfake-dep==2.*"


def test_a_package_no_index_has_is_absent_and_named(pip, tmp_path):
    '''What sends the job back for its wheel -- never relaxed, since no line
    of it is there.'''
    pip.absent = {"scfake-private"}
    pip.fail = ["ERROR: No matching distribution found for scfake-private==1.2.0"] * 3

    with pytest.raises(envinstall.InstallFailed) as raised:
        envinstall.install(packages(["scfake-bits==1.0", "scfake-private==1.2.0"]), [],
                           tmp_path, LOG, indexes=["https://pypi.org/simple/"])

    assert raised.value.result["absent"] == ["scfake-private"]
    assert "scfake-private" not in pip.calls[-1][1]


def test_an_index_that_cannot_be_asked_is_the_servers_failure(pip, tmp_path, monkeypatch):
    monkeypatch.setattr(pipbuild, "on_index", lambda name, indexes, proxy=None: None)
    monkeypatch.setattr(pipbuild, "listing", lambda name, version, indexes, proxy=None: None)
    pip.fail = "ERROR: No matching distribution found for scfake-bits==1.0"

    with pytest.raises(envinstall.InstallFailed) as raised:
        envinstall.install(packages(["scfake-bits==1.0"]), [], tmp_path, LOG)

    assert raised.value.result["network"] is True
    assert not raised.value.result.get("absent")


def test_a_line_conflicting_with_a_pinned_distribution_is_not_widened(pip, tmp_path):
    pip.fail = "The user requested (constraint) cocotb==2.1.0"

    with pytest.raises(envinstall.InstallFailed):
        envinstall.install(packages(["cocotb-bus==0.2.1"]), [], tmp_path, LOG)

    assert len(pip.calls) == 1


def test_nothing_to_add_runs_no_pip_and_is_still_an_environment(pip, tmp_path):
    '''Every requirement one this Python holds: nothing to install, and the
    listed versions it holds another of recorded.'''
    target, record = envinstall.install(packages(["pytest==0.0.1"]), [], tmp_path, LOG)

    assert pip.calls == []
    assert os.path.isdir(target)
    assert list(record["ignored"]) == ["pytest"]


def test_only_where_nodes_run_on_the_host_is_python_env_offered(tmp_path):
    from siliconcompiler.remote.server.config import Config

    (tmp_path / "config.json").write_text(json.dumps({"features": ["python.env"]}))
    assert "python.env" in Config.load(tmp_path)["features"]

    (tmp_path / "config.json").write_text(json.dumps(
        {"features": ["python.env"], "containers": True}))
    with pytest.raises(ValueError, match="python.env"):
        Config.load(tmp_path)


def test_what_an_install_added_is_kept_beside_it_for_a_cached_one(pip, tmp_path, monkeypatch):
    '''🔴 Where nodes run on the host there is no image, so the job-level log
    is the record of what the install added (profile §5) -- and a cached
    environment reports the same as the fresh one.'''
    monkeypatch.setattr(pipbuild, "installed", lambda site: [["scfake-bits", "2.0.1"]])

    first, fresh = envinstall.install(packages(["scfake-bits==2.0.1"]), [], tmp_path, LOG)
    again, cached = envinstall.install(packages(["scfake-bits==2.0.1"]), [], tmp_path, LOG)

    assert first == again and len(pip.calls) == 1
    assert fresh == cached == {"installed": [["scfake-bits", "2.0.1"]], "substituted": {},
                               "ignored": {}, "yanked": []}


def test_two_jobs_at_once_never_share_an_environment_or_a_cache(pip, tmp_path, monkeypatch):
    '''🔴 Host mode (implementation-notes §L): two jobs staging in one server
    are two threads, which the file lock does not keep apart -- the second to
    ask for a set waits and reuses what the first finished, and two sets
    install at once, each with a pip cache of its own.'''
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
            got.append(envinstall.install(packages(pins), [], tmp_path, LOG)[0])
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
