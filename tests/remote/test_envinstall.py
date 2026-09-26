import json
import logging
import os
import subprocess
import sys

import pytest

from siliconcompiler.remote import environment
from siliconcompiler.remote.server import envinstall


# A node's environment installed on the host, before the flow starts, into the
# user's own cache (surface D131's host mode). pip is faked: what is asserted is
# what it is handed, and what is left behind.


LOG = logging.getLogger("test")


@pytest.fixture
def pip(monkeypatch):
    '''Every pip call, and what the file it was handed said. Installs a marker
    into the target, or fails where told to.'''
    calls = []

    def fake(command, **kwargs):
        target = command[command.index("--target") + 1]
        handed = open(command[command.index("-r") + 1]).read()
        calls.append((command, handed))
        if fake.fail:
            return subprocess.CompletedProcess(command, 1, stdout="ERROR: no wheel for x")
        os.makedirs(target)
        open(os.path.join(target, "installed.txt"), "w").write(handed)
        return subprocess.CompletedProcess(command, 0, stdout="")

    fake.fail = False
    monkeypatch.setattr(subprocess, "run", fake)
    fake.calls = calls
    return fake


def parsed(text):
    return environment.parse(text.encode())


def test_the_uploaded_file_is_never_handed_to_pip(pip, tmp_path):
    '''🔴 Parsed and written again, so a line pip would read one way and the
    grammar another has no route through -- and wheels only.'''
    user = parsed("# the user's own comment\n--index-url https://pypi.org/simple/\n"
                  "numpy==2.0.1   # trailing\n")

    target = envinstall.install(user, tmp_path / "cache", LOG, "sim/0")

    (command, handed), = pip.calls
    assert command[:4] == [sys.executable, "-m", "pip", "install"]
    assert "--only-binary" in command and command[command.index("--only-binary") + 1] == ":all:"
    assert "the user's own comment" not in handed and "trailing" not in handed
    assert environment.parse(handed.encode()).pins == user.pins
    assert os.path.isdir(target)


def test_the_same_set_is_built_once_and_shared(pip, tmp_path):
    first = envinstall.install(parsed("numpy==2.0.1\n"), tmp_path, LOG, "a/0")
    again = envinstall.install(parsed("numpy==2.0.1\n"), tmp_path, LOG, "b/0")
    other = envinstall.install(parsed("numpy==2.0.2\n"), tmp_path, LOG, "c/0")

    assert first == again != other
    assert len(pip.calls) == 2


def test_one_that_will_not_install_says_which_and_leaves_nothing(pip, tmp_path):
    pip.fail = True

    with pytest.raises(RuntimeError) as raised:
        envinstall.install(parsed("numpy==2.0.1\n"), tmp_path, LOG, "sim/0")

    assert "sim/0" in str(raised.value) and sys.implementation.cache_tag in str(raised.value)
    assert "no wheel" in str(raised.value)
    assert not [path for path in tmp_path.iterdir() if not path.name.endswith(".lock")]


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

    assert envinstall.install_all(project, job, LOG) == ["sim/0"]

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
