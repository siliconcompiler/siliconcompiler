import pytest
import hashlib

from siliconcompiler import Project, Flowgraph, Design
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.vcd2fst.convert import Convert


def test_runtime_options_with_input_nodes(gcd_design):
    """Test vcd2fst runtime options when VCD comes from input nodes."""
    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("convert", Convert())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True
        arguments = node.task.get_runtime_arguments()
        assert arguments == [
            "--vcdname=inputs/gcd.vcd",
            "--fstname=outputs/gcd.fst"
        ]


def test_runtime_options_fallback_to_fileset(gcd_design):
    """Test vcd2fst falls back to fileset when inputs dir file doesn't exist."""
    from unittest.mock import patch, MagicMock

    proj = Project(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("convert", Convert())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "convert", "0")
    with node.runtime():
        assert node.setup() is True

        # Mock os.path.exists to return False for inputs/gcd.vcd
        # and mock get_file to return a specific VCD file path
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = False

            with patch.object(node.task.project, 'get_filesets') as mock_filesets:
                mock_lib = MagicMock()
                mock_lib.get_file.return_value = ["/home/examples/gcd/gcd.vcd"]
                mock_filesets.return_value = [(mock_lib, "rtl")]

                arguments = node.task.get_runtime_arguments()
                assert arguments == [
                    "--vcdname=/home/examples/gcd/gcd.vcd",
                    "--fstname=outputs/gcd.fst"
                ]


def test_tool_and_task_names():
    """Test vcd2fst tool and task names."""
    # Verify tool and task names
    assert Convert().tool() == "vcd2fst"
    assert Convert().task() == "convert"


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_vcd2fst_conversion():
    """Test vcd2fst actually converts VCD to FST and verify output hash."""
    # Create a minimal design with the test VCD file
    design = Design("random")
    with design.active_fileset("rtl"):
        design.set_topmodule("random")
        design.add_file("/home/pgadfort/siliconcompiler/tests/utils/data/random.vcd")

    proj = Project(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("convert", Convert())
    proj.set_flow(flow)

    # Run the conversion
    assert proj.run()

    # Find and hash the output FST file
    fst_file = proj.find_result("fst", "convert")
    assert fst_file is not None, "FST output file not found"

    # Compute SHA1 hash
    sha1_hash = hashlib.sha1()
    with open(fst_file, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha1_hash.update(chunk)

    assert sha1_hash.hexdigest() == "e56a8aeaf02a2743411a97f1426ae604da597a46"
