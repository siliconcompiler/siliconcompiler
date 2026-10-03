# Copyright 2026 Silicon Compiler Authors. All Rights Reserved.
import json
import logging
import os
import os.path
import subprocess

import pytest

from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools._common.cocotb import python_env
from siliconcompiler.tools.icarus.cocotb_exec import CocotbExecTask as IcarusCocotbExecTask
from siliconcompiler.utils import paths


def _make_distribution(site, name, version, requires=(), editable_source=None):
    '''Writes an installed distribution into site, as pip would.

    With editable_source the package lives there instead, and the install
    records that it is editable.
    '''
    dist_info = os.path.join(site, f"{name}-{version}.dist-info")
    os.makedirs(dist_info)
    with open(os.path.join(dist_info, "METADATA"), "w") as f:
        f.write(f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n")
        for req in requires:
            f.write(f"Requires-Dist: {req}\n")
    with open(os.path.join(dist_info, "top_level.txt"), "w") as f:
        f.write(f"{name}\n")

    package_root = editable_source or site
    os.makedirs(os.path.join(package_root, name))
    with open(os.path.join(package_root, name, "__init__.py"), "w") as f:
        f.write("")

    if editable_source:
        with open(os.path.join(dist_info, "direct_url.json"), "w") as f:
            json.dump({"url": f"file://{editable_source}", "dir_info": {"editable": True}}, f)

    return dist_info


@pytest.fixture
def site(monkeypatch):
    '''A directory on sys.path that fake distributions can be installed into.'''
    site = os.path.abspath("site")
    os.makedirs(site)
    monkeypatch.syspath_prepend(site)
    python_env._module_distributions.cache_clear()
    yield site
    python_env._module_distributions.cache_clear()


def test_imported_modules():
    with open("test_a.py", "w") as f:
        f.write("import os\nimport scfakeumi.sumi\nfrom cocotb.triggers import Timer\n"
                "from . import sibling\nimport numpy as np, json\n")
    with open("test_b.py", "w") as f:
        f.write("this is not python(\n")

    assert python_env.imported_modules(["test_a.py", "test_b.py", "missing.py"]) == \
        {"scfakeumi", "cocotb", "numpy"}


def test_capture_pins_index_distributions(site):
    _make_distribution(site, "scfakeumi", "0.3.1", requires=["scfakebits>=1"])
    _make_distribution(site, "scfakebits", "1.2.0")

    install, packages, forward, warnings = python_env.capture({"scfakeumi"}, [])

    assert install == ["scfakebits==1.2.0", "scfakeumi==0.3.1"]
    assert packages == []
    assert forward == []
    assert warnings == []


def test_capture_forwards_editable_distributions(site, monkeypatch):
    source = os.path.abspath("checkout")
    dist_info = _make_distribution(site, "scfakeumi", "0.3.1", editable_source=source)
    # What an editable install's .pth does at startup
    monkeypatch.syspath_prepend(source)

    install, packages, forward, _ = python_env.capture({"scfakeumi"}, [])

    assert install == []
    assert packages == ["scfakeumi==0.3.1"]
    # The package comes from the checkout, not the install's own file list
    assert forward == [os.path.join(source, "scfakeumi"), dist_info]


def test_capture_leaves_out_what_the_node_provides(site):
    # packaging is a siliconcompiler dependency, so the node already has it
    _make_distribution(site, "scfakeumi", "0.3.1", requires=["packaging", "siliconcompiler"])

    install, _, _, _ = python_env.capture({"scfakeumi"}, [])

    assert install == ["scfakeumi==0.3.1"]


def test_capture_follows_requested_extras(site):
    _make_distribution(site, "scfakeumi", "0.3.1",
                       requires=['scfakebits; extra == "sim"', 'scfakedocs; extra == "docs"'])
    _make_distribution(site, "scfakebits", "1.2.0")
    _make_distribution(site, "scfakedocs", "2.0.0")

    assert python_env.capture(set(), ["scfakeumi"])[0] == ["scfakeumi==0.3.1"]
    assert python_env.capture(set(), ["scfakeumi[sim]"])[0] == \
        ["scfakebits==1.2.0", "scfakeumi==0.3.1"]


def test_capture_ignores_modules_no_distribution_provides(site):
    assert python_env.capture({"adder_model"}, []) == ([], [], [], [])


def test_is_installed(site):
    _make_distribution(site, "scfakeumi", "0.3.1")

    assert python_env.is_installed("scfakeumi==0.3.1")
    assert not python_env.is_installed("scfakeumi==0.3.2")
    assert not python_env.is_installed("scfakenothing==1.0")


@pytest.fixture
def fake_pip(monkeypatch):
    '''Stands in for pip: records each call and creates what it would install.'''
    calls = []
    real_run = subprocess.run

    def run(cmd, **kwargs):
        if cmd[1:4] != ["-m", "pip", "install"]:
            return real_run(cmd, **kwargs)
        calls.append(cmd)
        target = cmd[cmd.index("--target") + 1]
        os.makedirs(target)
        for pin in cmd[cmd.index("--target") + 2:]:
            os.makedirs(os.path.join(target, pin.partition("==")[0]))
        return subprocess.CompletedProcess(cmd, 0, stdout="")

    monkeypatch.setattr(python_env.subprocess, "run", run)
    return calls


def test_install_builds_once_and_reuses(fake_pip):
    logger = logging.getLogger("test")

    first = python_env.install(["scfakeumi==0.3.1", "scfakebits==1.2.0"], "cache", logger)
    assert os.path.isdir(os.path.join(first, "scfakeumi"))
    assert len(fake_pip) == 1
    assert "--no-deps" in fake_pip[0]

    # Same set in another order: same directory, and pip is not run again
    second = python_env.install(["scfakebits==1.2.0", "scfakeumi==0.3.1"], "cache", logger)
    assert second == first
    assert len(fake_pip) == 1

    # A different set gets its own directory
    third = python_env.install(["scfakeumi==0.3.2"], "cache", logger)
    assert third != first
    assert len(fake_pip) == 2


def test_install_failure_leaves_nothing_behind(monkeypatch):
    def run(cmd, **kwargs):
        target = cmd[cmd.index("--target") + 1]
        os.makedirs(target)
        return subprocess.CompletedProcess(cmd, 1, stdout="no such version")

    monkeypatch.setattr(python_env.subprocess, "run", run)

    with pytest.raises(RuntimeError, match="no such version"):
        python_env.install(["scfakeumi==9.9.9"], "cache", logging.getLogger("test"))

    assert [f for f in os.listdir("cache") if not f.endswith(".lock")] == []


# ============================================================================
# CocotbEnvironment: capture where submitted, prepare on the node
# ============================================================================

TESTBENCH = "import cocotb\nimport scfakeumi\nimport scfakebits\n"


@pytest.fixture
def submitter_env(site, monkeypatch):
    '''The submitting machine: an editable scfakeumi and an index-installed scfakebits.'''
    source = os.path.abspath("checkout")
    dist_info = _make_distribution(site, "scfakeumi", "0.3.1", editable_source=source)
    monkeypatch.syspath_prepend(source)
    _make_distribution(site, "scfakebits", "1.2.0")
    return [os.path.join(source, "scfakeumi"), dist_info]


def test_setup_captures_environment(cocotb_project, cocotb_installed, submitter_env):
    proj = cocotb_project(IcarusCocotbExecTask(), source=TESTBENCH)

    node = SchedulerNode(proj, "simulate", "0")
    with node.runtime():
        assert node.setup() is True
        task = node.task
        install = task.get("var", "python_install")
        assert "scfakebits==1.2.0" in install
        assert all(not pin.startswith("scfakeumi") for pin in install)
        assert task.get("var", "python_forward_package") == ["scfakeumi==0.3.1"]
        assert task.get("var", "python_forward") == submitter_env
        assert task.get("var", "python_forward", field=None).get(field="copy") is True


def test_setup_keeps_capture_from_submitting_machine(cocotb_project, cocotb_installed,
                                                     submitter_env):
    # On the server the job carries a remote ID, and the client already captured
    proj = cocotb_project(IcarusCocotbExecTask(), source=TESTBENCH)
    proj.set("record", "remoteid", "0123456789abcdef")
    proj.set("tool", "icarus", "task", "exec_cocotb", "var", "python_install",
             ["fromclient==1.0"], step="simulate", index="0")

    node = SchedulerNode(proj, "simulate", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.get("var", "python_install") == ["fromclient==1.0"]
        assert node.task.get("var", "python_forward_package") == []


@pytest.fixture
def fake_install(monkeypatch):
    calls = []

    def install(pins, root, logger):
        calls.append(sorted(pins))
        return os.path.join(root, "installed")

    monkeypatch.setattr(python_env, "install", install)
    return calls


def test_pre_process_on_node_without_packages(cocotb_project, fake_install):
    # What the submitting machine captured, none of which this node has
    source = os.path.abspath("checkout")
    os.makedirs(os.path.join(source, "scfakeumi"))
    os.makedirs("scfakeumi-0.3.1.dist-info")
    proj = cocotb_project(IcarusCocotbExecTask())
    for key, value in (("python_install", ["scfakebits==1.2.0"]),
                       ("python_forward_package", ["scfakeumi==0.3.1"]),
                       ("python_forward", [os.path.join(source, "scfakeumi"),
                                           os.path.abspath("scfakeumi-0.3.1.dist-info")])):
        proj.set("tool", "icarus", "task", "exec_cocotb", "var", key, value,
                 step="simulate", index="0")

    node = SchedulerNode(proj, "simulate", "0")
    with node.runtime():
        os.makedirs(node.workdir)
        node.task.pre_process()
        python_path = node.task._get_python_path()
        envs = node.task.get_runtime_environmental_variables()

    staged = os.path.join(node.workdir, "cocotb_python")
    assert os.path.realpath(os.path.join(staged, "scfakeumi")) == os.path.join(source, "scfakeumi")
    assert os.path.isdir(os.path.join(staged, "scfakeumi-0.3.1.dist-info"))
    assert fake_install == [["scfakebits==1.2.0"]]

    installed = os.path.join(python_env_root(proj), "installed")
    assert python_path == [staged, installed]
    # After the test module directory, ahead of anything inherited
    assert envs["PYTHONPATH"].split(os.pathsep)[1:3] == [staged, installed]


def test_pre_process_where_packages_are_installed(cocotb_project, submitter_env, fake_install):
    # Running where the capture was made: nothing to stage or install
    proj = cocotb_project(IcarusCocotbExecTask())
    for key, value in (("python_install", ["scfakebits==1.2.0"]),
                       ("python_forward_package", ["scfakeumi==0.3.1"]),
                       ("python_forward", submitter_env)):
        proj.set("tool", "icarus", "task", "exec_cocotb", "var", key, value,
                 step="simulate", index="0")

    node = SchedulerNode(proj, "simulate", "0")
    with node.runtime():
        os.makedirs(node.workdir)
        node.task.pre_process()
        assert node.task._get_python_path() == []

    assert not os.path.exists(os.path.join(node.workdir, "cocotb_python"))
    assert fake_install == []


def python_env_root(proj):
    return os.path.join(paths.toolcachedir(proj), "cocotb", "python")
