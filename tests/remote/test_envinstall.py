import json
import logging
import os
import subprocess
import sys

import pytest

from siliconcompiler.remote import environment
from siliconcompiler.remote.server import envinstall


# A node's environment installed on the host while the job stages, into the
# user's own cache (host mode). pip is faked: what is asserted is what it is
# handed, and what is left behind.


LOG = logging.getLogger("test")


@pytest.fixture
def pip(monkeypatch):
    '''Every pip call, and what the file it was handed said. Installs a marker
    into the target, or fails where told to.'''
    calls = []

    def fake(command, **kwargs):
        import glob

        handed = open(command[command.index("-r") + 1]).read()
        constraints = open(command[command.index("-c") + 1]).read()
        calls.append((command, handed, constraints))
        fake.env = kwargs.get("env")
        if fake.fail:
            return subprocess.CompletedProcess(command, 1, stdout=fake.fail)
        # Into the environment whose Python ran it.
        environment = os.path.dirname(os.path.dirname(command[0]))
        site, = {os.path.realpath(path) for path in glob.glob(
            os.path.join(environment, "lib*", "python*", "site-packages"))}
        open(os.path.join(site, "installed.txt"), "w").write(handed)
        return subprocess.CompletedProcess(command, 0, stdout="")

    fake.fail = None
    monkeypatch.setattr(subprocess, "run", fake)
    fake.calls = calls
    return fake


def parsed(text):
    return environment.parse(text.encode())


def test_the_uploaded_file_is_never_handed_to_pip(pip, tmp_path, monkeypatch):
    '''🔴 Parsed and written again, so a line pip would read one way and the
    grammar another has no route through -- wheels only, from the
    deployment's indexes, and no pip configuration of anybody's.'''
    monkeypatch.setenv("PIP_INDEX_URL", "https://somewhere.example/simple/")
    user = parsed("# the user's own comment\nnumpy==2.0.1   # trailing\n")

    target = envinstall.install(user, tmp_path / "cache", LOG, ("sim", "0"),
                                indexes=["https://pypi.org/simple/",
                                         "https://extra.example/simple/"])

    (command, handed, _), = pip.calls
    assert command[1:4] == ["-m", "pip", "install"]
    assert "--only-binary" in command and command[command.index("--only-binary") + 1] == ":all:"
    assert command[command.index("--index-url") + 1] == "https://pypi.org/simple/"
    assert command[command.index("--extra-index-url") + 1] == "https://extra.example/simple/"
    assert "PIP_INDEX_URL" not in pip.env and pip.env["PIP_CONFIG_FILE"] == os.devnull
    assert "the user's own comment" not in handed and "trailing" not in handed
    assert environment.parse(handed.encode()).pins == user.pins
    assert os.path.isfile(os.path.join(target, "installed.txt"))


def test_what_requires_python_names_is_pinned_to_what_this_host_holds(pip, tmp_path):
    '''🔴 A venv that sees this Python's packages, with the job's
    `requires.python` pinned -- never `--target`, which ignores what is
    installed. The constraints are part of the key.'''
    from importlib import metadata

    first = envinstall.install(parsed("numpy==2.0.1\n"), tmp_path, LOG, ("sim", "0"),
                               constrain=["PyTest", "not-installed-anywhere"])
    other = envinstall.install(parsed("numpy==2.0.1\n"), tmp_path, LOG, ("sim", "0"))

    (command, _, constraints), _ = pip.calls
    assert "--target" not in command
    assert f"pytest=={metadata.version('pytest')}" in constraints.splitlines()
    assert "not-installed-anywhere" not in constraints
    assert first != other


def test_the_same_set_is_built_once_and_shared(pip, tmp_path):
    first = envinstall.install(parsed("numpy==2.0.1\n"), tmp_path, LOG, ("a", "0"))
    again = envinstall.install(parsed("numpy==2.0.1\n"), tmp_path, LOG, ("b", "0"))
    other = envinstall.install(parsed("numpy==2.0.2\n"), tmp_path, LOG, ("c", "0"))

    assert first == again != other
    assert len(pip.calls) == 2


def test_one_that_will_not_install_says_which_and_leaves_nothing(pip, tmp_path):
    pip.fail = "ERROR: no wheel for x"

    with pytest.raises(envinstall.InstallFailed) as raised:
        envinstall.install(parsed("numpy==2.0.1\n"), tmp_path, LOG, ("sim", "0"))

    assert "sim/0" in str(raised.value) and sys.implementation.cache_tag in str(raised.value)
    assert "no wheel" in str(raised.value)
    assert raised.value.node == ("sim", "0")
    assert not [path for path in tmp_path.iterdir() if not path.name.endswith(".lock")]


def test_a_version_that_does_not_install_is_tried_within_its_release_line(
        pip, tmp_path, monkeypatch):
    '''§L's order: the exact version, else one from its release line --
    `X.*`, or `0.Y.*` below 1.0 -- and the substitution recorded.'''
    from siliconcompiler.remote.server import pipbuild

    answers = iter(["ERROR: No matching distribution found for numpy==1.26.4\n"
                    "ERROR: No matching distribution found for tqdm==0.4.1", None])

    real = subprocess.run

    def once_then_fine(command, **kwargs):
        pip.fail = next(answers)
        return real(command, **kwargs)

    monkeypatch.setattr(subprocess, "run", once_then_fine)
    monkeypatch.setattr(pipbuild, "installed",
                        lambda site: [["numpy", "1.26.9"], ["tqdm", "0.4.7"]])

    envinstall.install(parsed("numpy==1.26.4\ntqdm==0.4.1\nsix==1.16.0\n"),
                       tmp_path, LOG, ("sim", "0"))

    (_, first, _), (_, second, _) = pip.calls
    assert "numpy==1.26.4" in first
    assert {"numpy==1.*", "tqdm==0.4.*", "six==1.16.0"} <= set(second.splitlines())


def test_a_line_conflicting_with_a_pinned_distribution_is_not_widened(pip, tmp_path):
    pip.fail = "The user requested (constraint) cocotb==2.1.0"

    with pytest.raises(envinstall.InstallFailed):
        envinstall.install(parsed("cocotb-bus==0.2.1\n"), tmp_path, LOG, ("sim", "0"))

    assert len(pip.calls) == 1


def test_every_node_is_installed_and_linked_where_its_task_looks(pip, gcd_design):
    from siliconcompiler import Flowgraph, Project
    from siliconcompiler.scheduler import SchedulerNode
    from siliconcompiler.tools.builtin.nop import NOPTask
    from siliconcompiler.utils.paths import jobdir

    project = Project(gcd_design)
    project.add_fileset("rtl")
    flow = Flowgraph("tbflow")
    flow.node("sim", NOPTask())
    project.set_flow(flow)
    project.option.set_builddir(os.path.abspath("build"))
    project.option.set_cachedir(os.path.abspath("cache"))

    job = jobdir(project)
    for node, text in ((("sim", "0"), "numpy==2.0.1\n"), (("idle", "0"), "# nothing\n")):
        path = os.path.join(job, environment.path_for(*node))
        os.makedirs(os.path.dirname(path))
        open(path, "w").write(text)

    installed = envinstall.install_all(job, os.path.abspath("cache/python-env"), LOG,
                                       [("sim", "0"), ("idle", "0"), ("other", "0")])
    assert [node for node, _ in installed] == [("sim", "0")]

    site = os.path.join(job, environment.site_path("sim", "0"))
    assert os.path.islink(site)
    assert os.path.realpath(site).startswith(os.path.abspath("cache"))   # the user's own
    node = SchedulerNode(project, "sim", "0")
    with node.runtime():
        path = node.task.get_runtime_environmental_variables()["PYTHONPATH"]
    assert site in path.split(os.pathsep)


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
    from siliconcompiler.remote.server import pipbuild

    monkeypatch.setattr(pipbuild, "installed", lambda site: [["numpy", "2.0.1"]])

    first = envinstall.install(parsed("numpy==2.0.1\n"), tmp_path, LOG, ("a", "0"))
    again = envinstall.install(parsed("numpy==2.0.1\n"), tmp_path, LOG, ("b", "0"))

    assert first == again and len(pip.calls) == 1
    assert envinstall.recorded(again) == {"installed": [["numpy", "2.0.1"]],
                                          "substituted": {}}
