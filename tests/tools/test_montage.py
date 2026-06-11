import os

import pytest

from siliconcompiler import Project, Flowgraph
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.montage import tile, convert


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_version(gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("version", tile.TileTask())
    proj.set_flow(flow)

    tile.TileTask.find_task(proj).set_montage_bins(2, 2)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


def test_runtime_opts(gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("tile", tile.TileTask())
    proj.set_flow(flow)

    tile.TileTask.find_task(proj).set_montage_bins(4, 3)

    node = SchedulerNode(proj, "tile", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.get_threads() == 1
        arguments = node.task.get_runtime_arguments()
        assert len(arguments) == 17
        assert arguments == [
            'inputs/gcd_X0_Y0.png', 'inputs/gcd_X1_Y0.png',
            'inputs/gcd_X2_Y0.png', 'inputs/gcd_X3_Y0.png',
            'inputs/gcd_X0_Y1.png', 'inputs/gcd_X1_Y1.png',
            'inputs/gcd_X2_Y1.png', 'inputs/gcd_X3_Y1.png',
            'inputs/gcd_X0_Y2.png', 'inputs/gcd_X1_Y2.png',
            'inputs/gcd_X2_Y2.png', 'inputs/gcd_X3_Y2.png',
            '-tile', '4x3', '-geometry', '+0+0', 'outputs/gcd.png']


def test_runtime_opts_autodetect_bins(gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("tile", tile.TileTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "tile", "0")
    with node.runtime():
        # Pretend upstream nodes provided a 3x2 grid of tile images; bins is
        # left unset so it must be inferred from the filenames.
        node.task.get_files_from_input_nodes = lambda: {
            f"gcd_X{x}_Y{y}.png": [("up", "0")]
            for x in range(3) for y in range(2)
        }

        assert node.setup() is True
        assert node.task.get("var", "bins") == (3, 2)

        arguments = node.task.get_runtime_arguments()
        assert arguments == [
            'inputs/gcd_X0_Y0.png', 'inputs/gcd_X1_Y0.png', 'inputs/gcd_X2_Y0.png',
            'inputs/gcd_X0_Y1.png', 'inputs/gcd_X1_Y1.png', 'inputs/gcd_X2_Y1.png',
            '-tile', '3x2', '-geometry', '+0+0', 'outputs/gcd.png']


def test_policy_generation(gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("tile", tile.TileTask())
    proj.set_flow(flow)

    tile.TileTask.find_task(proj).set_montage_bins(2, 2)

    node = SchedulerNode(proj, "tile", "0")
    with node.runtime():
        assert node.setup() is True

        # MAGICK_CONFIGURE_PATH must point ImageMagick at the work directory.
        envvars = node.task.get_runtime_environmental_variables()
        assert envvars["MAGICK_CONFIGURE_PATH"] == node.task.nodeworkdir

        # pre_process must write a policy.xml covering every resource limit.
        # The work directory is normally created by the scheduler before
        # execution; create it here so pre_process can write into it.
        os.makedirs(node.task.nodeworkdir, exist_ok=True)
        node.task.pre_process()
        policy_file = os.path.join(node.task.nodeworkdir, "policy.xml")
        assert os.path.exists(policy_file)
        with open(policy_file) as f:
            policy = f.read()
        for resource in ("memory", "map", "disk", "width", "height", "area"):
            assert f'name="{resource}"' in policy


def test_convert_runtime_opts(gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    convert.ConvertTask.find_task(proj).set_convert_format("jpg")
    convert.ConvertTask.find_task(proj).set_convert_resize("1024x1024")
    convert.ConvertTask.find_task(proj).set_convert_quality(85)

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()
        assert arguments == [
            'inputs/gcd.png',
            '-resize', '1024x1024',
            '-quality', '85',
            'outputs/gcd.jpg']


def test_convert_no_resize(gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()
        assert arguments == [
            'inputs/gcd.png',
            'outputs/gcd.png']


def test_convert_detects_input_format(gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        # Pretend an upstream node provided a WEBP image instead of a PNG.
        node.task.get_files_from_input_nodes = lambda: {"gcd.webp": [("up", "0")]}

        assert node.task._input_image() == "gcd.webp"

        arguments = node.task.runtime_options()
        assert "inputs/gcd.webp" in arguments
        assert "outputs/gcd.png" in arguments


def test_convert_defaults_to_png(gcd_design):
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("convert", convert.ConvertTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        # No recognizable image among the inputs -> fall back to PNG.
        node.task.get_files_from_input_nodes = lambda: {"gcd.txt": [("up", "0")]}

        assert node.task._input_image() == "gcd.png"
