import pytest

import os.path

from pathlib import Path

from siliconcompiler import Project, Flowgraph, Design
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.chisel import convert


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_version(gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("version", convert.ConvertTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_chisel(datadir, sbt_download_guard):
    design = Design("gcd")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("GCD")
        design.add_file("GCD.scala")

    proj = Project(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    with sbt_download_guard():
        assert proj.run()

    # check that compilation succeeded
    assert proj.find_result('v', step='convert') == \
        os.path.abspath("build/gcd/job0/convert/0/outputs/GCD.v")


def test_runtime_args(datadir):
    design = Design("gcd")
    design.set_dataroot("root", datadir)
    with design.active_dataroot("root"), design.active_fileset("rtl"):
        design.set_topmodule("GCD")
        design.add_file("GCD.scala")

    proj = Project(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()
        assert arguments == [
            '-batch',
            '--server',
            '--no-share',
            '--no-global',
            'runMain SCDriver --module GCD --output-file ../outputs/GCD.v']


def test_chisel_parameter_application():
    task = convert.ConvertTask()
    task.set_chisel_application('test_app')
    assert task.get("var", "application") == 'test_app'
    task.set_chisel_application('other_app', step='convert', index='1')
    assert task.get("var", "application", step='convert', index='1') == 'other_app'
    assert task.get("var", "application") == 'test_app'


def test_chisel_parameter_argument():
    task = convert.ConvertTask()
    task.add_chisel_argument('--threads 2')
    assert task.get("var", "argument") == ['--threads 2']
    task.add_chisel_argument('--no-mem-init')
    assert task.get("var", "argument") == ['--threads 2', '--no-mem-init']
    task.add_chisel_argument('--no-check-comb-loops', step='convert', index='1')
    assert task.get("var", "argument", step='convert', index='1') == ['--no-check-comb-loops']
    assert task.get("var", "argument") == ['--threads 2', '--no-mem-init']
    task.add_chisel_argument(['--no-reset'], clobber=True)
    assert task.get("var", "argument") == ['--no-reset']


def test_chisel_parameter_targetdir():
    task = convert.ConvertTask()
    task.set_chisel_targetdir('build')
    assert task.get("var", "targetdir") == 'build'
    task.set_chisel_targetdir('gen', step='convert', index='1')
    assert task.get("var", "targetdir", step='convert', index='1') == 'gen'
    assert task.get("var", "targetdir") == 'build'


# ============================================================================
# COURSIER_CACHE
#
# ConvertTask duplicates the three checks the CCache mixin makes, so these
# mirror the mixin's own tests: divergence between the two shows up here.
# ============================================================================

@pytest.fixture
def convert_node(datadir, monkeypatch):
    '''A set-up chisel convert node, with no ambient coursier cache.'''
    monkeypatch.delenv("COURSIER_CACHE", raising=False)

    def _make(cachedir=None):
        design = Design("gcd")
        design.set_dataroot("root", datadir)
        with design.active_dataroot("root"), design.active_fileset("rtl"):
            design.set_topmodule("GCD")
            design.add_file("GCD.scala")

        proj = Project(design)
        proj.add_fileset("rtl")
        if cachedir:
            proj.option.set_cachedir(cachedir)

        flow = Flowgraph("testflow")
        flow.node("convert", convert.ConvertTask())
        proj.set_flow(flow)

        return proj, SchedulerNode(proj, "convert", "0")

    return _make


def env_of(node, include_path=False):
    with node.runtime():
        assert node.setup() is True
        return node.task.get_runtime_environmental_variables(include_path=include_path)


def test_coursier_cache(convert_node):
    """sbt re-resolves every jar on each run; the tool cache is what it keeps."""
    _, node = convert_node("thiscache")

    # Compared as paths: a configured cachedir comes back from find_files
    # posix-style, which on Windows is not what abspath() spells.
    assert Path(env_of(node)["COURSIER_CACHE"]) == \
        Path(os.path.abspath("thiscache")) / "tools" / "chisel"


def test_coursier_cache_user_setting_wins(convert_node, monkeypatch):
    monkeypatch.setenv("COURSIER_CACHE", "/user/coursier")
    _, node = convert_node()

    assert "COURSIER_CACHE" not in env_of(node)


def test_coursier_cache_task_setting_wins(convert_node):
    proj, node = convert_node()
    assert convert.ConvertTask.find_task(proj).set("env", "COURSIER_CACHE", "/task/coursier")

    assert env_of(node)["COURSIER_CACHE"] == "/task/coursier"


def test_coursier_cache_empty_ambient_setting_is_not_a_setting(convert_node, monkeypatch):
    """COURSIER_CACHE= names no directory, so coursier uses its own default."""
    monkeypatch.setenv("COURSIER_CACHE", "")
    _, node = convert_node("thiscache")

    assert Path(env_of(node)["COURSIER_CACHE"]) == \
        Path(os.path.abspath("thiscache")) / "tools" / "chisel"


def test_coursier_cache_survives_the_node_export(convert_node, monkeypatch):
    """The node exports these and then asks again, to write the replay script."""
    _, node = convert_node("thiscache")

    first = env_of(node)["COURSIER_CACHE"]
    monkeypatch.setenv("COURSIER_CACHE", first)

    assert env_of(node)["COURSIER_CACHE"] == first
