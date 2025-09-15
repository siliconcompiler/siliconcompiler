import hashlib
import json
import pytest

import os.path

from siliconcompiler.tools.klayout import export
from siliconcompiler.tools.klayout import operations
from siliconcompiler.tools.klayout import drc
from siliconcompiler.tools.klayout import convert_drc_db

from siliconcompiler.targets import freepdk45_demo

from siliconcompiler import ASICProject, Flowgraph, Design
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.klayout.export import ExportTask
from siliconcompiler.tools.klayout import KLayoutLibrary

from tools.inputimporter import ImporterTask


@pytest.fixture
def setup_pdk_test(monkeypatch, datadir):
    # pytest's monkeypatch lets us modify sys.path for this test only.
    monkeypatch.syspath_prepend(datadir)


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
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
@pytest.mark.ready
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

    proj = ASICProject(design)
    proj.add_fileset(["layout"])
    proj.load_target(freepdk45_demo.setup)
    proj.add_asiclib(lib)

    flow = Flowgraph("testflow")
    flow.node('import', ImporterTask())
    flow.node("export", export.ExportTask())
    flow.edge('import', 'export')
    proj.set_flow(flow)

    proj.get_task(filter=ImporterTask).set("var", "input_files",
                                           os.path.join(datadir, 'heartbeat_wrapper.def'))

    proj.get_task(filter=export.ExportTask).set("var", "timestamps", False)

    assert proj.run()
    result = proj.find_result('gds', 'export')
    assert os.path.isfile(result)
    with open(result, 'rb') as gds_file:
        data = gds_file.read()
        assert hashlib.md5(data).hexdigest() == '033839a1f1597c15c6ce7e4de24a15d5'


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
def test_klayout_operations(datadir):
    design = Design("heartbeat")
    with design.active_fileset("layout"):
        design.set_topmodule("heartbeat")

    proj = ASICProject(design)
    proj.add_fileset(["layout"])
    proj.load_target(freepdk45_demo.setup)

    flow = Flowgraph("testflow")
    flow.node('import', ImporterTask())
    flow.node("ops1", operations.OperationsTask())
    flow.node("ops2", operations.OperationsTask())
    flow.edge('import', 'ops1')
    flow.edge('ops1', 'ops2')
    proj.set_flow(flow)

    proj.get_task(filter=ImporterTask).set("var", "input_files",
                                           os.path.join(datadir, 'heartbeat.gds'))
    ops: operations.OperationsTask = proj.get_task(filter=operations.OperationsTask)
    ops.set("var", "timestamps", False)

    # Ops1
    ops.add_operation("rotate", None, step="ops1")
    ops.add_operation("write", "rotate.gds", step="ops1")
    ops.add_operation("rotate", None, step="ops1")
    ops.add_operation("outline", "var,outline", step="ops1")
    ops.set("var", "outline", ["255", "0"])
    ops.add_operation("write", "outline.gds", step="ops1")
    ops.add_operation("rename", "var,name", step="ops1")
    ops.set("var", "name", "new_name", step="ops1")
    ops.add_operation("write", "rename.gds", step="ops1")

    # Ops2
    ops.add_operation("merge", "rotate.gds", step="ops2")
    ops.add_operation("write", "rotate.gds", step="ops2")
    ops.add_operation("add", "outline.gds", step="ops2")
    ops.add_operation("write", "outline.gds", step="ops2")
    ops.add_operation("add_top", "var,name", step="ops2")
    ops.set("var", "name", "new_top", step="ops2")
    ops.add_operation("write", "add_top.gds", step="ops2")
    ops.add_operation("rename_cell", "var,rename_cell", step="ops2")
    ops.set("var", "rename_cell", "AND4_X1=AND_dummy", step="ops2")
    ops.add_operation("write", "rename_cells.gds", step="ops2")

    assert proj.run()

    ops1_result = proj.getworkdir(step='ops1')
    for op_file, op_hash in [('rotate.gds', '0048802f8d2fedf038cb6cfdc5ebc989'),
                             ('outline.gds', '4bf006f5f465ec9c42cd1ef80677424e'),
                             ('rename.gds', '4991f2267811517b8f7e73924b92128e')]:
        path = os.path.join(ops1_result, 'outputs', op_file)
        assert os.path.exists(path)
        with open(path, 'rb') as gds_file:
            data = gds_file.read()
            assert hashlib.md5(data).hexdigest() == op_hash

    ops2_result = proj.getworkdir(step='ops2')
    for op_file, op_hash in [('rotate.gds', 'ee2e5b9646ca4f7e941dd1767af47188'),
                             ('outline.gds', '753e1a252baaa6c9dbb3e9528a3eef3c'),
                             ('add_top.gds', '2c6f39ff49088278bafa51adfd761e61'),
                             ('rename_cells.gds', '4253ee90771c0fcaf0c4c95010783cef')]:
        path = os.path.join(ops2_result, 'outputs', op_file)
        assert os.path.exists(path)
        with open(path, 'rb') as gds_file:
            data = gds_file.read()
            assert hashlib.md5(data).hexdigest() == op_hash


@pytest.mark.nocache
def test_pdk(setup_pdk_test):
    import klayout_pdk

    assert klayout_pdk.FauxPDK().check_filepaths()


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
def test_drc_pass(setup_pdk_test, datadir):
    import klayout_pdk

    design = Design("testdesign")
    with design.active_fileset("layout"):
        design.set_topmodule("interposer")

    proj = ASICProject(design)
    proj.add_fileset(["layout"])
    proj.set_pdk(klayout_pdk.FauxPDK())
    proj.set_asic_delaymodel("nldm")
    proj.set_mainlib("testdesign")

    flow = Flowgraph("testflow")
    flow.node('import', ImporterTask())
    flow.node("drc", drc.DRCTask())
    flow.edge('import', 'drc')
    proj.set_flow(flow)

    proj.get_task(filter=ImporterTask).set(
        "var", "input_files", os.path.join(datadir, "klayout_pdk", 'interposer.gds'))
    proj.get_task(filter=drc.DRCTask).set("var", "drc_name", "drc")

    assert proj.run()
    assert proj.history("job0").get('metric', 'drcs', step='drc', index='0') == 0


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
def test_drc_fail(setup_pdk_test, datadir):
    import klayout_pdk

    design = Design("testdesign")
    with design.active_fileset("layout"):
        design.set_topmodule("interposer")

    proj = ASICProject(design)
    proj.add_fileset(["layout"])
    proj.set_pdk(klayout_pdk.FauxPDK())
    proj.set_asic_delaymodel("nldm")
    proj.set_mainlib("testdesign")

    flow = Flowgraph("testflow")
    flow.node('import', ImporterTask())
    flow.node("drc", drc.DRCTask())
    flow.edge('import', 'drc')
    proj.set_flow(flow)

    proj.get_task(filter=ImporterTask).set(
        "var", "input_files", os.path.join(datadir, "klayout_pdk", "withdrcs", 'interposer.gds'))
    proj.get_task(filter=drc.DRCTask).set("var", "drc_name", "drc")

    assert proj.run()
    assert proj.history("job0").get('metric', 'drcs', step='drc', index='0') == 12


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
def test_convert_drc(setup_pdk_test, datadir):
    import klayout_pdk

    design = Design("testdesign")
    with design.active_fileset("layout"):
        design.set_topmodule("interposer")

    proj = ASICProject(design)
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

    proj.get_task(filter=ImporterTask).set(
        "var", "input_files", os.path.join(datadir, "klayout_pdk", "withdrcs", 'interposer.gds'))
    proj.get_task(filter=drc.DRCTask).set("var", "drc_name", "drc")

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
