import hashlib
import json
import pytest
import struct

import os.path

from siliconcompiler.tools.klayout import export
from siliconcompiler.tools.klayout import operations
from siliconcompiler.tools.klayout import drc
from siliconcompiler.tools.klayout import convert_drc_db
from siliconcompiler.tools.klayout import merge
from siliconcompiler.tools.klayout import img2stream

from siliconcompiler.targets import freepdk45_demo, ihp130_demo

from siliconcompiler import ASIC, Flowgraph, Design, TaskSkip
from siliconcompiler.flows.img2streamflow import Img2StreamFlow
from siliconcompiler.flows.highresscreenshotflow import HighResScreenshotFlow
from siliconcompiler.tools.builtin.importfiles import ImportFilesTask
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.klayout.export import ExportTask
from siliconcompiler.tools.klayout import KLayoutLibrary
from siliconcompiler.tools.klayout import screenshot

from tools.inputimporter import ImporterTask
from siliconcompiler.utils.paths import workdir


@pytest.fixture
def setup_pdk_test(monkeypatch, datadir):
    # pytest's monkeypatch lets us modify sys.path for this test only.
    monkeypatch.syspath_prepend(datadir)


def __asic_heartbeat(step, task):
    design = Design("heartbeat")
    with design.active_fileset("layout"):
        design.set_topmodule("heartbeat")

    proj = ASIC(design)
    proj.add_fileset("layout")
    freepdk45_demo(proj)

    flow = Flowgraph("testflow")
    flow.node(step, task)
    proj.set_flow(flow)

    return proj


@pytest.fixture
def asic_heartbeat_ops():
    '''A single node operations flow, for exercising setup().'''
    proj = __asic_heartbeat("prepare", operations.OperationsTask())
    return proj, operations.OperationsTask.find_task(proj)


@pytest.fixture
def asic_heartbeat_screenshot():
    '''A single node screenshot flow, for exercising setup().'''
    proj = __asic_heartbeat("screenshot", screenshot.ScreenshotTask())
    return proj, screenshot.ScreenshotTask.find_task(proj)


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_version(asic_gcd):
    flow = Flowgraph("testflow")
    flow.node("version", ExportTask())
    asic_gcd.set_flow(flow)

    node = SchedulerNode(asic_gcd, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_export(datadir):
    lib = KLayoutLibrary()
    lib.set_name("heartbeat")
    with lib.active_fileset("models.physical"):
        lib.add_file(os.path.join(datadir, 'heartbeat.gds'))
        lib.add_file(os.path.join(datadir, 'heartbeat.lef'))
        lib.add_asic_aprfileset()

    design = Design("testdesign")
    with design.active_fileset("layout"):
        design.set_topmodule("heartbeat_wrapper")

    proj = ASIC(design)
    proj.add_fileset(["layout"])
    freepdk45_demo(proj)
    proj.add_asiclib(lib)

    flow = Flowgraph("testflow")
    flow.node('import', ImporterTask())
    flow.node("export", export.ExportTask())
    flow.edge('import', 'export')
    proj.set_flow(flow)

    ImporterTask.find_task(proj).set("var", "input_files",
                                     os.path.join(datadir, 'heartbeat_wrapper.def'))

    export.ExportTask.find_task(proj).set("var", "timestamps", False)

    assert proj.run()
    result = proj.find_result('gds', 'export')
    assert os.path.isfile(result)
    with open(result, 'rb') as gds_file:
        data = gds_file.read()
        assert hashlib.md5(data).hexdigest() == '6ff562b5568a9926848f61e4436ee911'


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_klayout_operations(datadir):
    design = Design("heartbeat")
    with design.active_fileset("layout"):
        design.set_topmodule("heartbeat")

    proj = ASIC(design)
    proj.add_fileset(["layout"])
    freepdk45_demo(proj)

    flow = Flowgraph("testflow")
    flow.node('import', ImporterTask())
    flow.node("ops1", operations.OperationsTask())
    flow.node("ops2", operations.OperationsTask())
    flow.edge('import', 'ops1')
    flow.edge('ops1', 'ops2')
    proj.set_flow(flow)

    ImporterTask.find_task(proj).set("var", "input_files",
                                     os.path.join(datadir, 'heartbeat.gds'))
    ops: operations.OperationsTask = operations.OperationsTask.find_task(proj)
    ops.set("var", "timestamps", False)

    # Ops1: repeated and interleaved operations within a single node
    ops.add_klayout_operation(operations.Rotate(90), step="ops1")
    ops.add_klayout_operation(operations.Write("rotate.gds"), step="ops1")
    ops.add_klayout_operation(operations.Rotate(90), step="ops1")
    ops.add_klayout_operation(operations.Outline(255, 0), step="ops1")
    ops.add_klayout_operation(operations.Write("outline.gds"), step="ops1")
    ops.add_klayout_operation(operations.RenameTop("new_name"), step="ops1")
    ops.add_klayout_operation(operations.Write("rename.gds"), step="ops1")

    # Ops2
    ops.add_klayout_operation(operations.Merge(input="rotate.gds"), step="ops2")
    ops.add_klayout_operation(operations.Write("rotate.gds"), step="ops2")
    ops.add_klayout_operation(operations.Add(input="outline.gds"), step="ops2")
    ops.add_klayout_operation(operations.Write("outline.gds"), step="ops2")
    ops.add_klayout_operation(operations.AddTop("new_top"), step="ops2")
    ops.add_klayout_operation(operations.Write("add_top.gds"), step="ops2")
    ops.add_klayout_operation(operations.RenameCell([("AND4_X1", "AND_dummy")]), step="ops2")
    ops.add_klayout_operation(operations.Write("rename_cells.gds"), step="ops2")

    assert proj.run()

    ops1_result = workdir(proj, step='ops1')
    for op_file, op_hash in [('rotate.gds', '0048802f8d2fedf038cb6cfdc5ebc989'),
                             ('outline.gds', '4bf006f5f465ec9c42cd1ef80677424e'),
                             ('rename.gds', '4991f2267811517b8f7e73924b92128e')]:
        path = os.path.join(ops1_result, 'outputs', op_file)
        assert os.path.exists(path)
        with open(path, 'rb') as gds_file:
            data = gds_file.read()
            assert hashlib.md5(data).hexdigest() == op_hash

    ops2_result = workdir(proj, step='ops2')
    for op_file, op_hash in [('rotate.gds', 'ee2e5b9646ca4f7e941dd1767af47188'),
                             ('outline.gds', '753e1a252baaa6c9dbb3e9528a3eef3c'),
                             ('add_top.gds', '2c6f39ff49088278bafa51adfd761e61'),
                             ('rename_cells.gds', '4253ee90771c0fcaf0c4c95010783cef')]:
        path = os.path.join(ops2_result, 'outputs', op_file)
        assert os.path.exists(path)
        with open(path, 'rb') as gds_file:
            data = gds_file.read()
            assert hashlib.md5(data).hexdigest() == op_hash


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_klayout_screenshot(datadir):
    '''The untiled screenshot path honors resolution, margin, linewidth and
    oversampling.'''
    design = Design("heartbeat")
    with design.active_fileset("layout"):
        design.set_topmodule("heartbeat")

    proj = ASIC(design)
    proj.add_fileset(["layout"])
    freepdk45_demo(proj)

    flow = Flowgraph("testflow")
    flow.node('import', ImporterTask())
    flow.node("screenshot", screenshot.ScreenshotTask())
    flow.edge('import', 'screenshot')
    proj.set_flow(flow)

    ImporterTask.find_task(proj).set("var", "input_files",
                                     os.path.join(datadir, 'heartbeat.gds'))

    task = screenshot.ScreenshotTask.find_task(proj)
    task.set_klayout_resolution(800, 600)
    task.set_klayout_margin(5)
    task.set_klayout_linewidth(2)
    task.set_klayout_oversampling(2)

    assert proj.run()

    png = proj.find_result("png", step="screenshot")
    assert png is not None
    assert os.path.isfile(png)

    with open(png, 'rb') as image:
        width, height = struct.unpack(">II", image.read(24)[16:24])
    assert (width, height) == (800, 600)


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_klayout_screenshot_hide_layers(datadir):
    '''Layers hidden through the task reach the tool, alongside the PDK's.'''
    design = Design("heartbeat")
    with design.active_fileset("layout"):
        design.set_topmodule("heartbeat")

    proj = ASIC(design)
    proj.add_fileset(["layout"])
    freepdk45_demo(proj)

    flow = Flowgraph("testflow")
    flow.node('import', ImporterTask())
    flow.node("screenshot", screenshot.ScreenshotTask())
    flow.edge('import', 'screenshot')
    proj.set_flow(flow)

    ImporterTask.find_task(proj).set("var", "input_files",
                                     os.path.join(datadir, 'heartbeat.gds'))

    task = screenshot.ScreenshotTask.find_task(proj)
    task.set_klayout_resolution(200, 200)
    # metal1 by name (as spelled in the PDK's .lyp), via1 by layer/datatype
    task.add_klayout_hidelayers(["metal1.drawing", "12/0"])

    assert proj.run()

    with open(os.path.join(workdir(proj, step="screenshot"), "screenshot.log")) as log:
        hidden = [line for line in log if "Turning off layer" in line]

    assert any("metal1.drawing" in line for line in hidden)
    assert any("12/0" in line for line in hidden)


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_klayout_highres_screenshot_flow(datadir):
    '''An unconfigured prepare node skips, so the flow runs out of the box.'''
    design = Design("heartbeat")
    with design.active_fileset("layout"):
        design.set_topmodule("heartbeat")

    proj = ASIC(design)
    proj.add_fileset(["layout"])
    freepdk45_demo(proj)
    proj.set_flow(HighResScreenshotFlow())

    ImportFilesTask.find_task(proj).add_import_file(os.path.join(datadir, 'heartbeat.gds'))
    screenshot.ScreenshotTask.find_task(proj).set_klayout_resolution(400, 400)

    assert proj.run()
    assert os.path.isfile(proj.find_result("png", step="screenshot"))


@pytest.mark.nocache
def test_pdk(setup_pdk_test):
    import klayout_pdk

    assert klayout_pdk.FauxPDK().check_filepaths()


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_drc_pass(setup_pdk_test, datadir):
    import klayout_pdk

    design = Design("testdesign")
    with design.active_fileset("layout"):
        design.set_topmodule("interposer")

    proj = ASIC(design)
    proj.add_fileset(["layout"])
    proj.set_pdk(klayout_pdk.FauxPDK())
    proj.set_asic_delaymodel("nldm")
    proj.set_mainlib("testdesign")

    flow = Flowgraph("testflow")
    flow.node('import', ImporterTask())
    flow.node("drc", drc.DRCTask())
    flow.edge('import', 'drc')
    proj.set_flow(flow)

    ImporterTask.find_task(proj).set(
        "var", "input_files", os.path.join(datadir, "klayout_pdk", 'interposer.gds'))
    drc.DRCTask.find_task(proj).set("var", "drc_name", "drc")

    assert proj.run()
    assert proj.history("job0").get('metric', 'drcs', step='drc', index='0') == 0


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_drc_fail(setup_pdk_test, datadir):
    import klayout_pdk

    design = Design("testdesign")
    with design.active_fileset("layout"):
        design.set_topmodule("interposer")

    proj = ASIC(design)
    proj.add_fileset(["layout"])
    proj.set_pdk(klayout_pdk.FauxPDK())
    proj.set_asic_delaymodel("nldm")
    proj.set_mainlib("testdesign")

    flow = Flowgraph("testflow")
    flow.node('import', ImporterTask())
    flow.node("drc", drc.DRCTask())
    flow.edge('import', 'drc')
    proj.set_flow(flow)

    ImporterTask.find_task(proj).set(
        "var", "input_files", os.path.join(datadir, "klayout_pdk", "withdrcs", 'interposer.gds'))
    drc.DRCTask.find_task(proj).set("var", "drc_name", "drc")

    assert proj.run()
    assert proj.history("job0").get('metric', 'drcs', step='drc', index='0') == 12


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_convert_drc(setup_pdk_test, datadir):
    import klayout_pdk

    design = Design("testdesign")
    with design.active_fileset("layout"):
        design.set_topmodule("interposer")

    proj = ASIC(design)
    proj.add_fileset(["layout"])
    proj.set_pdk(klayout_pdk.FauxPDK())
    proj.set_asic_delaymodel("nldm")
    proj.set_mainlib("testdesign")

    flow = Flowgraph("testflow")
    flow.node('import', ImporterTask())
    flow.node("drc", drc.DRCTask())
    flow.node("convert", convert_drc_db.ConvertDRCDBTask())
    flow.edge('import', 'drc')
    flow.edge('drc', 'convert')
    proj.set_flow(flow)

    ImporterTask.find_task(proj).set(
        "var", "input_files", os.path.join(datadir, "klayout_pdk", "withdrcs", 'interposer.gds'))
    drc.DRCTask.find_task(proj).set("var", "drc_name", "drc")

    assert proj.run()
    assert proj.history("job0").get('metric', 'drcs', step='drc', index='0') == 12

    lyrdb = proj.find_result("lyrdb", step="convert", directory="inputs")
    assert os.path.isfile(lyrdb)
    odb_json = proj.find_result('json', step='convert')
    assert os.path.isfile(odb_json)

    with open(odb_json, 'r') as f:
        data = json.load(f)

    assert "interposer.lyrdb" in data
    assert "source" in data["interposer.lyrdb"]

    assert data["interposer.lyrdb"]["source"] == lyrdb
    data["interposer.lyrdb"]["source"] = "sourcefile"

    assert "category" in data["interposer.lyrdb"]
    assert len(data["interposer.lyrdb"]["category"]) == 3
    for cat in data["interposer.lyrdb"]["category"]:
        assert data["interposer.lyrdb"]["category"][cat]["source"] == lyrdb
        data["interposer.lyrdb"]["category"][cat]["source"] = "sourcefile"

    assert hashlib.sha1(json.dumps(data, sort_keys=True).encode()).hexdigest() == \
        '6ee3d048a257ccb7f2c0e86333b2044d0173c5c0'


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_img2stream():
    design = Design("testdesign")
    design.set_dataroot("sc", "python://siliconcompiler")
    with design.active_fileset("image"):
        design.set_topmodule("logo")
        design.add_file("data/logo.png", dataroot="sc")

    proj = ASIC(design)
    proj.add_fileset("image")

    ihp130_demo(proj)

    proj.set_flow(Img2StreamFlow(drc="klayout"))

    task = img2stream.Img2StreamTask.find_task(proj)
    # 15 x 15 logo
    task.set_klayout_minsize(100.0)
    task.set_klayout_targetwidth(1500.0)
    task.set_klayout_layer(134)

    # test optional outline layer path
    task.set_klayout_outline_layer(189)  # prBoundary
    task.set_klayout_fill_exclusion_layer(134, 4)  # NoMetFiller

    task.set_klayout_invert(True)
    task.set_klayout_timestamp(False)

    drc.DRCTask.find_task(proj).set_klayout_drcname("drc")

    assert proj.run()

    gds = proj.find_result("gds", step="image")
    lef = proj.find_result("lef", step="image")
    assert os.path.isfile(gds)
    assert os.path.isfile(lef)

    with open(gds, 'rb') as gds_file:
        data = gds_file.read()
        assert hashlib.md5(data).hexdigest() == "0c8a1f81af4a731ecb4f86f3f4bac591"

    with open(lef, 'r') as lef_file:
        assert lef_file.read() == """MACRO logo
  CLASS COVER ;
  ORIGIN 0.0000 0.0000 ;
  FOREIGN logo -0.0000 -0.0000 ;
  SIZE 1500.0000 BY 1400.0000 ;
  SYMMETRY X Y R90 ;
  OBS
    LAYER TopMetal2 ;
      POLYGON 0.0000 0.0000 0.0000 1400.0000 1500.0000 1400.0000 1500.0000 0.0000 ;
    LAYER DIEAREA ;
      POLYGON 0.0000 0.0000 0.0000 1400.0000 1500.0000 1400.0000 1500.0000 0.0000 ;
  END
END logo
"""

    assert proj.history("job0").get('metric', 'drcs', step='drc', index='0') == 0


def test_klayout_operation_types():
    types = operations.get_operation_types()
    assert set(types) == {
        "add", "add_top", "convert_property", "delete_layers", "flatten", "merge",
        "merge_shapes", "outline", "rename", "rename_cell", "rotate", "swap", "write"
    }
    for optype, cls in types.items():
        assert cls().optype == optype


def test_klayout_add_operation():
    task = operations.OperationsTask()

    op = task.add_klayout_operation(operations.Rotate(180))
    assert isinstance(op, operations.Rotate)
    assert op.name == "rotate0"
    assert task.get("var", "operations") == [("rotate", "rotate0")]
    assert task.get("var", "rotate0.angle") == 180
    assert op.get_angle() == 180


def test_klayout_add_operation_sequence():
    '''Repeats and interleaving within a single node.'''
    task = operations.OperationsTask()

    task.add_klayout_operation(operations.Add(input="guard_edge.gds"))
    task.add_klayout_operation(operations.Rotate(90))
    task.add_klayout_operation(operations.Write("rot90.gds"))
    task.add_klayout_operation(operations.Outline(255, 0))
    task.add_klayout_operation(operations.Rotate(180))
    task.add_klayout_operation(operations.Write("rot270.gds"))

    assert task.get("var", "operations") == [
        ("add", "add0"),
        ("rotate", "rotate0"),
        ("write", "write0"),
        ("outline", "outline0"),
        ("rotate", "rotate1"),
        ("write", "write1")
    ]

    assert task.get("var", "rotate0.angle") == 90
    assert task.get("var", "rotate1.angle") == 180
    assert task.get("var", "write0.filename") == "rot90.gds"
    assert task.get("var", "write1.filename") == "rot270.gds"
    assert task.get("var", "outline0.layer") == (255, 0)
    assert task.get("var", "add0.input") == "guard_edge.gds"


def test_klayout_add_operation_pernode():
    task = operations.OperationsTask()

    task.add_klayout_operation(operations.Rotate(90), step="ops1")
    task.add_klayout_operation(operations.Flatten(), step="ops2")

    assert task.get("var", "operations", step="ops1", index="0") == [("rotate", "rotate0")]
    assert task.get("var", "operations", step="ops2", index="0") == [("flatten", "flatten0")]
    assert task.get("var", "operations") == []


def test_klayout_add_operation_shared():
    '''An operation can be referenced from more than one node.'''
    task = operations.OperationsTask()

    strip = task.add_klayout_operation(
        operations.DeleteLayers([(10, 0)], name="strip"), step="ops1")
    task.add_klayout_operation(operations.DeleteLayers(name="strip"), step="ops2")

    assert task.get("var", "operations", step="ops1", index="0") == [("delete_layers", "strip")]
    assert task.get("var", "operations", step="ops2", index="0") == [("delete_layers", "strip")]
    assert strip.get_layers() == [(10, 0)]

    # per-node override of a shared operation
    strip.set_layers([(20, 5)], step="ops2", index="0")
    assert strip.get_layers(step="ops1", index="0") == [(10, 0)]
    assert strip.get_layers(step="ops2", index="0") == [(20, 5)]


def test_klayout_add_operation_names_stable():
    '''Names are allocated, not positional, so inserting one does not renumber.'''
    task = operations.OperationsTask()

    task.add_klayout_operation(operations.Rotate(90))
    task.add_klayout_operation(operations.Rotate(180))
    before = {key: task.get("var", key) for key in task.getkeys("var") if "." in key}

    task.add_klayout_operation(operations.Rotate(270))

    for key, value in before.items():
        assert task.get("var", key) == value
    assert task.get("var", "rotate2.angle") == 270


def test_klayout_add_operation_invalid_name():
    with pytest.raises(ValueError, match="is not a valid operation name"):
        operations.Rotate(name="bad.name")


def test_klayout_add_operation_duplicate_name():
    task = operations.OperationsTask()
    task.add_klayout_operation(operations.Rotate(90, name="spin"))

    with pytest.raises(ValueError, match="already defined"):
        task.add_klayout_operation(operations.Rotate(180, name="spin"))


def test_klayout_add_operation_invalid_type():
    task = operations.OperationsTask()
    with pytest.raises(TypeError, match="op must be a KLayoutOperation"):
        task.add_klayout_operation(operations.Rotate)


def test_klayout_operation_unbound_setters():
    '''Setters work before the operation is added to a task.'''
    op = operations.DeleteLayers()
    op.add_layer(1, 0)
    op.add_layer(2, 5)
    assert op.get_layers() == [(1, 0), (2, 5)]

    task = operations.OperationsTask()
    task.add_klayout_operation(op)
    assert op.get_layers() == [(1, 0), (2, 5)]
    assert task.get("var", "delete_layers0.layers") == [(1, 0), (2, 5)]


def test_klayout_operation_handle_setters():
    task = operations.OperationsTask()

    delete = task.add_klayout_operation(operations.DeleteLayers([(63, 0)]))
    delete.add_layer(550, 26)
    assert delete.get_layers() == [(63, 0), (550, 26)]
    delete.set_layers([(1, 1)])
    assert delete.get_layers() == [(1, 1)]

    convert = task.add_klayout_operation(operations.ConvertProperty((10, 2), 3, (85, 5)))
    assert convert.get_source() == (10, 2)
    assert convert.get_property() == "3"
    assert convert.get_dest() == (85, 5)

    cells = task.add_klayout_operation(operations.SwapCell([("a", "b")]))
    cells.add_cell("c", "d")
    assert cells.get_cells() == [("a", "b"), ("c", "d")]

    shapes = task.add_klayout_operation(operations.MergeShapes(all=True))
    assert shapes.get_all() is True

    merge = task.add_klayout_operation(operations.Merge(file="fill.gds"))
    assert merge.get_file() == ["fill.gds"]
    assert task.get("var", "merge0.file", field=None).is_file


def test_klayout_get_operations():
    task = operations.OperationsTask()
    task.add_klayout_operation(operations.Rotate(90), step="ops1")
    task.add_klayout_operation(operations.Write("out.gds"), step="ops1")

    ops = task.get_klayout_operations(step="ops1", index="0")
    assert [type(op) for op in ops] == [operations.Rotate, operations.Write]
    assert ops[0].get_angle() == 90
    assert ops[1].get_filename() == "out.gds"

    assert task.get_klayout_operations() == []


def test_klayout_remove_operation():
    task = operations.OperationsTask()
    task.add_klayout_operation(operations.Rotate(90), step="ops1")
    strip = task.add_klayout_operation(operations.DeleteLayers([(10, 0)]), step="ops1")

    assert task.remove_klayout_operation(strip, step="ops1") is True
    assert task.get("var", "operations", step="ops1", index="0") == [("rotate", "rotate0")]
    assert not task.valid("var", "delete_layers0.layers")

    assert task.remove_klayout_operation("delete_layers0", step="ops1") is False


def test_klayout_remove_operation_still_referenced():
    '''Parameters survive while another node still refers to the operation.'''
    task = operations.OperationsTask()
    task.add_klayout_operation(operations.DeleteLayers([(10, 0)], name="strip"), step="ops1")
    task.add_klayout_operation(operations.DeleteLayers(name="strip"), step="ops2")

    assert task.remove_klayout_operation("strip", step="ops1") is True
    assert task.get("var", "operations", step="ops1", index="0") == []
    assert task.valid("var", "strip.layers")

    assert task.remove_klayout_operation("strip", step="ops2") is True
    assert not task.valid("var", "strip.layers")


def test_klayout_operations_manifest_roundtrip():
    task = operations.OperationsTask()
    task.add_klayout_operation(operations.DeleteLayers([(63, 0), (550, 26)]), step="ops1")
    task.add_klayout_operation(operations.Rotate(180), step="ops1")
    task.add_klayout_operation(operations.Write("out.gds"), step="ops1")

    manifest = json.loads(json.dumps(task.getdict()))

    reloaded = operations.OperationsTask()
    reloaded._from_dict(manifest, ("tool", "klayout", "task", "operations"))

    ops = reloaded.get_klayout_operations(step="ops1", index="0")
    assert [type(op) for op in ops] == [
        operations.DeleteLayers, operations.Rotate, operations.Write]
    assert ops[0].get_layers() == [(63, 0), (550, 26)]
    assert ops[1].get_angle() == 180
    assert ops[2].get_filename() == "out.gds"


def test_klayout_add_operation_legacy():
    task = operations.OperationsTask()

    with pytest.warns(DeprecationWarning, match="use add_klayout_operation"):
        task.add_operation("rotate", None)
    with pytest.warns(DeprecationWarning):
        task.add_operation("write", "out.gds")
    with pytest.warns(DeprecationWarning):
        task.add_operation("merge", "fill.gds")

    assert task.get("var", "operations") == [
        ("rotate", "rotate0"), ("write", "write0"), ("merge", "merge0")]
    assert task.get("var", "write0.filename") == "out.gds"
    assert task.get("var", "merge0.input") == "fill.gds"


def test_klayout_add_operation_legacy_keypath():
    task = operations.OperationsTask()

    with pytest.warns(DeprecationWarning):
        with pytest.raises(ValueError, match="use DeleteLayers instead"):
            task.add_operation("delete_layers", "var,layers")


def test_klayout_operations_setup(asic_heartbeat_ops):
    proj, task = asic_heartbeat_ops

    task.add_klayout_operation(operations.DeleteLayers([(10, 0)]), step="prepare")
    task.add_klayout_operation(operations.Merge(input="fill.gds"), step="prepare")
    task.add_klayout_operation(operations.Write("mid.gds"), step="prepare")

    node = SchedulerNode(proj, "prepare", "0")
    with node.runtime():
        node.task.setup()

        require = node.task.get("require", step="prepare", index="0")
        prefix = "tool,klayout,task,operations,var,"
        assert f"{prefix}operations" in require
        assert f"{prefix}delete_layers0.layers" in require
        assert f"{prefix}merge0.input" in require
        assert f"{prefix}write0.filename" in require

        assert "mid.gds" in node.task.get("output", step="prepare", index="0")
        assert "fill.gds" in node.task.get("input", step="prepare", index="0")


def test_klayout_operations_setup_empty(asic_heartbeat_ops):
    '''A node with no operations skips rather than running klayout for nothing.'''
    proj, _ = asic_heartbeat_ops

    node = SchedulerNode(proj, "prepare", "0")
    with node.runtime():
        with pytest.raises(TaskSkip, match="no operations to perform"):
            node.task.setup()


@pytest.mark.parametrize("op,error", [
    (operations.Outline(), "outline 'outline0' requires a layer"),
    (operations.RenameTop(), "rename 'rename0' requires a cellname"),
    (operations.RenameCell(), "rename_cell 'rename_cell0' requires cells"),
    (operations.DeleteLayers(), "delete_layers 'delete_layers0' requires layers"),
    (operations.MergeShapes(), "merge_shapes 'merge_shapes0' requires layers or all"),
    (operations.ConvertProperty(), "convert_property 'convert_property0' requires a source"),
    (operations.Write(), "write 'write0' requires a filename"),
    (operations.Merge(), "merge 'merge0' requires a file or an input"),
    (operations.Merge(file="a.gds", input="b.gds"),
     "merge 'merge0' cannot set both file and input"),
])
def test_klayout_operations_setup_incomplete(asic_heartbeat_ops, op, error):
    proj, task = asic_heartbeat_ops

    task.add_klayout_operation(op, step="prepare")

    node = SchedulerNode(proj, "prepare", "0")
    with node.runtime():
        with pytest.raises(ValueError, match=error):
            node.task.setup()


def test_klayout_task_hide_layers():
    task = operations.OperationsTask()

    task.add_klayout_hidelayers("metal1")
    task.add_klayout_hidelayers(["metal2", "10/0"])
    assert task.get("var", "hide_layers") == ["metal1", "metal2", "10/0"]

    task.add_klayout_hidelayers("metal3", clobber=True)
    assert task.get("var", "hide_layers") == ["metal3"]

    # a per node value replaces rather than extends the global one
    task.add_klayout_hidelayers("metal4", step="show", index="0")
    assert task.get("var", "hide_layers", step="show", index="0") == ["metal4"]
    assert task.get("var", "hide_layers") == ["metal3"]


def test_klayout_parameter_stream():
    task = operations.OperationsTask()
    task.set_klayout_stream('oas')
    assert task.get("var", "stream") == 'oas'
    task.set_klayout_stream('gds', step='op', index='1')
    assert task.get("var", "stream", step='op', index='1') == 'gds'
    assert task.get("var", "stream") == 'oas'


def test_klayout_parameter_timestamps():
    task = operations.OperationsTask()
    task.set_klayout_timestamps(False)
    assert task.get("var", "timestamps") is False
    task.set_klayout_timestamps(True, step='op', index='1')
    assert task.get("var", "timestamps", step='op', index='1') is True
    assert task.get("var", "timestamps") is False


def test_klayout_export_parameter_stream():
    task = export.ExportTask()
    task.set_klayout_stream('oas')
    assert task.get("var", "stream") == 'oas'
    task.set_klayout_stream('gds', step='export', index='1')
    assert task.get("var", "stream", step='export', index='1') == 'gds'
    assert task.get("var", "stream") == 'oas'


def test_klayout_export_parameter_timestamps():
    task = export.ExportTask()
    task.set_klayout_timestamps(False)
    assert task.get("var", "timestamps") is False
    task.set_klayout_timestamps(True, step='export', index='1')
    assert task.get("var", "timestamps", step='export', index='1') is True
    assert task.get("var", "timestamps") is False


def test_klayout_export_parameter_screenshot():
    task = export.ExportTask()
    task.set_klayout_screenshot(False)
    assert task.get("var", "screenshot") is False
    task.set_klayout_screenshot(True, step='export', index='1')
    assert task.get("var", "screenshot", step='export', index='1') is True
    assert task.get("var", "screenshot") is False


def test_klayout_drc_parameter_drcname():
    task = drc.DRCTask()
    task.set_klayout_drcname('test1')
    assert task.get("var", "drc_name") == 'test1'
    task.set_klayout_drcname('test2', step='drc', index='1')
    assert task.get("var", "drc_name", step='drc', index='1') == 'test2'
    assert task.get("var", "drc_name") == 'test1'


def test_klayout_merge_parameter_reference():
    task = merge.Merge()
    task.set_klayout_reference('fs', 'lib1', 'fileset1')
    assert task.get("var", "reference") == ('fs', 'lib1', 'fileset1')
    task.set_klayout_reference('input', 'step1', '0', step='merge', index='1')
    assert task.get("var", "reference", step='merge', index='1') == ('input', 'step1', '0')
    assert task.get("var", "reference") == ('fs', 'lib1', 'fileset1')


def test_klayout_merge_parameter_reference_fileset_conversion():
    task = merge.Merge()
    task.set_klayout_reference('fileset', 'lib1', 'fileset1')
    # Should convert 'fileset' to 'fs'
    assert task.get("var", "reference") == ('fs', 'lib1', 'fileset1')


def test_klayout_merge_parameter_add_merge():
    task = merge.Merge()
    task.add_klayout_merge('fs', 'lib1', 'fileset1', 'prefix1')
    assert task.get("var", "merge") == [('fs', 'lib1', 'fileset1', 'prefix1')]
    task.add_klayout_merge('input', 'step1', '0', 'prefix2', step='merge', index='1')
    assert task.get("var", "merge", step='merge', index='1') == \
        [('input', 'step1', '0', 'prefix2')]
    assert task.get("var", "merge") == [('fs', 'lib1', 'fileset1', 'prefix1')]
    task.add_klayout_merge('fs', 'lib2', 'fileset2', 'prefix3', clobber=True)
    assert task.get("var", "merge") == [('fs', 'lib2', 'fileset2', 'prefix3')]


def test_klayout_merge_parameter_add_merge_fileset_conversion():
    task = merge.Merge()
    task.add_klayout_merge('fileset', 'lib1', 'fileset1', 'prefix1')
    # Should convert 'fileset' to 'fs'
    assert task.get("var", "merge") == [('fs', 'lib1', 'fileset1', 'prefix1')]


def test_drc_runset_required(setup_pdk_test):
    # Regression guard (P1): the DRC runset deck resolved in runtime_options must be
    # declared required so it is hashed (cache) and copied (remote runs).
    import klayout_pdk

    design = Design("testdesign")
    with design.active_fileset("layout"):
        design.set_topmodule("interposer")

    proj = ASIC(design)
    proj.add_fileset(["layout"])
    proj.set_pdk(klayout_pdk.FauxPDK())
    proj.set_asic_delaymodel("nldm")
    proj.set_mainlib("testdesign")

    flow = Flowgraph("testflow")
    flow.node("drc", drc.DRCTask())
    proj.set_flow(flow)

    drc.DRCTask.find_task(proj).set("var", "drc_name", "drc")

    node = SchedulerNode(proj, "drc", "0")
    with node.runtime():
        assert node.setup() is True
        requires = node.task.get("require")

    pdk_name = proj.get("asic", "pdk")
    assert f"library,{pdk_name},pdk,drc,runsetfileset,klayout,drc" in requires, requires
    assert any(r.startswith(f"library,{pdk_name},fileset,") and r.endswith("file,drc")
               for r in requires), requires
