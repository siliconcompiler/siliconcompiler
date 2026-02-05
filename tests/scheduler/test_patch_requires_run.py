"""Tests for patch change detection in requires_run()."""
import os
import pytest
import difflib
from siliconcompiler import Design, Project, Task
from siliconcompiler.flowgraph import Flowgraph
from siliconcompiler.scheduler.schedulernode import SchedulerNode, SchedulerNodeReset


class FileUsingTask(Task):
    """A task that actually requires files from the fileset."""
    def tool(self):
        return 'testingtool'
    
    def task(self):
        return 'testingtask'
    
    def setup(self):
        # Require the fileset files using add_required_key
        # This properly adds the keypaths that get_check_changed_keys() will return
        for fileset in self.project.get("option", "fileset"):
            self.add_required_key(self.project.design, "fileset", fileset, "file", "verilog")
    
    def run(self):
        pass


def create_test_design_with_files(tmp_path, num_files=2):
    """Create a design with multiple test files."""
    design = Design("testdesign")
    
    # Create test files
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    
    files = []
    for i in range(num_files):
        module_path = src_dir / f"module{i}.v"
        module_path.write_text(f"module test{i};\n  wire a;\nendmodule\n")
        files.append(module_path)
    
    design.set_dataroot("src", str(src_dir))
    
    with design.active_fileset("rtl"), design.active_dataroot("src"):
        design.set_topmodule("test0")
        for i in range(num_files):
            design.add_file(f"module{i}.v")
    
    return design, files


def add_patch(design, filename, patch_name="fix1"):
    """Add a patch to a design."""
    original = f"module test;\n  wire a;\nendmodule\n"
    modified = f"module test;\n  wire a, b;\nendmodule\n"
    patch_text = ''.join(difflib.unified_diff(
        original.splitlines(keepends=True),
        modified.splitlines(keepends=True),
        fromfile=filename,
        tofile=filename
    ))
    
    patch = design.get("fileset", "rtl", "patch", patch_name, field="schema")
    patch.set('file', filename)
    patch.set('file', 'src', field='dataroot')
    patch.set('diff', patch_text)


def setup_node_with_manifests(design, tmp_path):
    """Setup a node and write its manifests."""
    flow = Flowgraph("testflow")
    flow.node("step1", FileUsingTask())
    
    proj = Project(design)
    proj.set_flow(flow)
    proj.set("option", "fileset", "rtl")
    
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    proj.set("option", "builddir", str(build_dir))
    proj.set("option", "jobname", "testjob")
    
    node = SchedulerNode(proj, "step1", "0")
    
    # Call setup() to register the task requirements
    node.setup()
    
    os.makedirs(os.path.dirname(node.get_manifest(input=True)), exist_ok=True)
    os.makedirs(os.path.dirname(node.get_manifest(input=False)), exist_ok=True)
    
    # Set status to success so requires_run will actually check
    proj.set('record', 'status', 'success', step='step1', index='0')
    
    # Write the manifest AFTER setup() so it includes the requirements
    proj.write_manifest(node.get_manifest(input=True))
    proj.write_manifest(node.get_manifest(input=False))
    
    return proj, node


def test_patch_no_change(tmp_path, monkeypatch):
    """Test that having patches but not changing them doesn't trigger rerun."""
    import logging
    
    design, files = create_test_design_with_files(tmp_path, num_files=2)
    add_patch(design, "module0.v", "fix1")
    
    proj, node = setup_node_with_manifests(design, tmp_path)
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    
    # Create a new node - should not raise since nothing changed
    new_node = SchedulerNode(proj, "step1", "0")
    
    # This should NOT raise because the patch hasn't changed
    try:
        with new_node.runtime():
            new_node.requires_run()
        # If we get here, the node doesn't require a rerun (which is correct)
        assert True
    except SchedulerNodeReset:
        pytest.fail("Node should not require rerun when patch is unchanged")


def test_patch_change_not_in_required_files(tmp_path, monkeypatch):
    """Test that changing a patch for a file in a different fileset doesn't trigger rerun."""
    import logging
    
    design, files = create_test_design_with_files(tmp_path, num_files=2)
    
    # Add a file to a DIFFERENT fileset (tb) that's not required by the task
    tb_dir = tmp_path / "tb"
    tb_dir.mkdir()
    tb_file = tb_dir / "testbench.v"
    tb_file.write_text("module tb; endmodule\n")
    
    design.set_dataroot("tb", str(tb_dir))
    with design.active_fileset("tb"), design.active_dataroot("tb"):
        design.add_file("testbench.v")
    
    # Add patch for testbench.v which is NOT in the required fileset
    add_patch(design, "testbench.v", "fix1")
    # Set the fileset for the patch
    patch = design.get("fileset", "rtl", "patch", "fix1", field="schema")
    # Actually, patches are per-fileset, so we need to add it to the tb fileset
    original = "module tb;\nendmodule\n"
    modified = "module tb;\n  wire a;\nendmodule\n"
    patch_text = ''.join(difflib.unified_diff(
        original.splitlines(keepends=True),
        modified.splitlines(keepends=True),
        fromfile='testbench.v',
        tofile='testbench.v'
    ))
    
    patch_tb = design.get("fileset", "tb", "patch", "fix1", field="schema")
    patch_tb.set('file', 'testbench.v')
    patch_tb.set('file', 'tb', field='dataroot')
    patch_tb.set('diff', patch_text)
    
    proj, node = setup_node_with_manifests(design, tmp_path)
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    
    # Now change the patch for testbench.v
    modified2 = "module tb;\n  wire a, b;\nendmodule\n"
    patch_text2 = ''.join(difflib.unified_diff(
        original.splitlines(keepends=True),
        modified2.splitlines(keepends=True),
        fromfile='testbench.v',
        tofile='testbench.v'
    ))
    
    patch_tb = design.get("fileset", "tb", "patch", "fix1", field="schema")
    patch_tb.set('diff', patch_text2)
    
    # Create new node
    new_node = SchedulerNode(proj, "step1", "0")
    
    # This should NOT raise because testbench.v is in a different fileset
    try:
        with new_node.runtime():
            new_node.requires_run()
        # If we get here, the node doesn't require a rerun (which is correct)
        assert True
    except SchedulerNodeReset:
        pytest.fail("Node should not require rerun when patch affects file in unrequired fileset")


def test_patch_change_in_required_file(tmp_path, monkeypatch):
    """Test that changing a patch for a required file triggers rerun."""
    import logging
    
    design, files = create_test_design_with_files(tmp_path, num_files=2)
    
    # Add patch for module0.v which IS used
    add_patch(design, "module0.v", "fix1")
    
    proj, node = setup_node_with_manifests(design, tmp_path)
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    
    # Now change the patch for module0.v
    original = "module test;\n  wire a;\nendmodule\n"
    modified = "module test;\n  wire a, b, c;\nendmodule\n"  # Different change
    patch_text = ''.join(difflib.unified_diff(
        original.splitlines(keepends=True),
        modified.splitlines(keepends=True),
        fromfile='module0.v',
        tofile='module0.v'
    ))
    
    patch = design.get("fileset", "rtl", "patch", "fix1", field="schema")
    patch.set('diff', patch_text)
    
    # Create new node
    new_node = SchedulerNode(proj, "step1", "0")
    
    # This SHOULD raise because module0.v is in the node's required files
    with pytest.raises(SchedulerNodeReset, match='Patch rtl/fix1 field "diff" modified'):
        with new_node.runtime():
            new_node.requires_run()


def test_patch_added_not_required(tmp_path, monkeypatch):
    """Test that adding a patch for a file in an unrequired fileset doesn't trigger rerun."""
    import logging
    
    design, files = create_test_design_with_files(tmp_path, num_files=2)
    
    # Add a file to a DIFFERENT fileset (tb) that's not required by the task
    tb_dir = tmp_path / "tb"
    tb_dir.mkdir()
    tb_file = tb_dir / "testbench.v"
    tb_file.write_text("module tb; endmodule\n")
    
    design.set_dataroot("tb", str(tb_dir))
    with design.active_fileset("tb"), design.active_dataroot("tb"):
        design.add_file("testbench.v")
    
    proj, node = setup_node_with_manifests(design, tmp_path)
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    
    # Now add a patch for testbench.v (in the 'tb' fileset, not 'rtl')
    original = "module tb;\nendmodule\n"
    modified = "module tb;\n  wire a;\nendmodule\n"
    patch_text = ''.join(difflib.unified_diff(
        original.splitlines(keepends=True),
        modified.splitlines(keepends=True),
        fromfile='testbench.v',
        tofile='testbench.v'
    ))
    
    patch_tb = design.get("fileset", "tb", "patch", "fix1", field="schema")
    patch_tb.set('file', 'testbench.v')
    patch_tb.set('file', 'tb', field='dataroot')
    patch_tb.set('diff', patch_text)
    
    # Create new node
    new_node = SchedulerNode(proj, "step1", "0")
    
    # This should NOT raise because testbench.v is in a different fileset
    try:
        with new_node.runtime():
            new_node.requires_run()
        assert True
    except SchedulerNodeReset:
        pytest.fail("Node should not require rerun when patch added for file in unrequired fileset")


def test_patch_added_required(tmp_path, monkeypatch):
    """Test that adding a patch for a required file triggers rerun."""
    import logging
    
    design, files = create_test_design_with_files(tmp_path, num_files=2)
    
    proj, node = setup_node_with_manifests(design, tmp_path)
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    
    # Now add a patch for module0.v (required)
    add_patch(design, "module0.v", "fix1")
    
    # Create new node
    new_node = SchedulerNode(proj, "step1", "0")
    
    # This SHOULD raise
    with pytest.raises(SchedulerNodeReset, match='Patch rtl/fix1 added'):
        with new_node.runtime():
            new_node.requires_run()


def test_patch_removed_not_required(tmp_path, monkeypatch):
    """Test that removing a patch for a file in an unrequired fileset doesn't trigger rerun."""
    import logging
    
    design, files = create_test_design_with_files(tmp_path, num_files=2)
    
    # Add a file to a DIFFERENT fileset (tb) that's not required by the task
    tb_dir = tmp_path / "tb"
    tb_dir.mkdir()
    tb_file = tb_dir / "testbench.v"
    tb_file.write_text("module tb; endmodule\n")
    
    design.set_dataroot("tb", str(tb_dir))
    with design.active_fileset("tb"), design.active_dataroot("tb"):
        design.add_file("testbench.v")
    
    # Start with patch for testbench.v (in the 'tb' fileset, not 'rtl')
    original = "module tb;\nendmodule\n"
    modified = "module tb;\n  wire a;\nendmodule\n"
    patch_text = ''.join(difflib.unified_diff(
        original.splitlines(keepends=True),
        modified.splitlines(keepends=True),
        fromfile='testbench.v',
        tofile='testbench.v'
    ))
    
    patch_tb = design.get("fileset", "tb", "patch", "fix1", field="schema")
    patch_tb.set('file', 'testbench.v')
    patch_tb.set('file', 'tb', field='dataroot')
    patch_tb.set('diff', patch_text)
    
    proj, node = setup_node_with_manifests(design, tmp_path)
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    
    # Remove the patch
    design.remove("fileset", "tb", "patch", "fix1")
    
    # Create new node
    new_node = SchedulerNode(proj, "step1", "0")
    
    # This should NOT raise because testbench.v is in a different fileset
    try:
        with new_node.runtime():
            new_node.requires_run()
        assert True
    except SchedulerNodeReset:
        pytest.fail("Node should not require rerun when patch removed for file in unrequired fileset")


def test_patch_removed_required(tmp_path, monkeypatch):
    """Test that removing a patch for a required file triggers rerun."""
    import logging
    
    design, files = create_test_design_with_files(tmp_path, num_files=2)
    
    # Start with patch for module0.v (required)
    add_patch(design, "module0.v", "fix1")
    
    proj, node = setup_node_with_manifests(design, tmp_path)
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    
    # Remove the patch
    design.remove("fileset", "rtl", "patch", "fix1")
    
    # Create new node
    new_node = SchedulerNode(proj, "step1", "0")
    
    # This SHOULD raise
    with pytest.raises(SchedulerNodeReset, match='Patch rtl/fix1 removed'):
        with new_node.runtime():
            new_node.requires_run()


def test_patch_file_field_changed_to_required(tmp_path, monkeypatch):
    """Test that changing a patch's file field to target a required file triggers rerun."""
    import logging
    
    design, files = create_test_design_with_files(tmp_path, num_files=2)
    
    # Start with patch for module1.v (not required)
    add_patch(design, "module1.v", "fix1")
    
    proj, node = setup_node_with_manifests(design, tmp_path)
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    
    # Change patch to target module0.v (required)
    patch = design.get("fileset", "rtl", "patch", "fix1", field="schema")
    patch.set('file', 'module0.v')
    
    # Create new node
    new_node = SchedulerNode(proj, "step1", "0")
    
    # This SHOULD raise
    with pytest.raises(SchedulerNodeReset, match='Patch rtl/fix1 field "file" modified'):
        with new_node.runtime():
            new_node.requires_run()


def test_patch_file_field_changed_from_required(tmp_path, monkeypatch):
    """Test that changing a patch's file field away from a required file triggers rerun."""
    import logging
    
    design, files = create_test_design_with_files(tmp_path, num_files=2)
    
    # Start with patch for module0.v (required)
    add_patch(design, "module0.v", "fix1")
    
    proj, node = setup_node_with_manifests(design, tmp_path)
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    
    # Change patch to target module1.v (not required)
    patch = design.get("fileset", "rtl", "patch", "fix1", field="schema")
    patch.set('file', 'module1.v')
    
    # Create new node
    new_node = SchedulerNode(proj, "step1", "0")
    
    # This SHOULD raise because the previous file was required
    with pytest.raises(SchedulerNodeReset, match='Patch rtl/fix1 field "file" modified'):
        with new_node.runtime():
            new_node.requires_run()


def test_no_patches_no_fileset(tmp_path, monkeypatch):
    """Test that having no patches and no fileset doesn't cause errors."""
    import logging
    
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("test")
    
    flow = Flowgraph("testflow")
    flow.node("step1", FileUsingTask())
    
    proj = Project(design)
    proj.set_flow(flow)
    proj.set("option", "fileset", "rtl")  # Set the fileset
    
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    proj.set("option", "builddir", str(build_dir))
    proj.set("option", "jobname", "testjob")
    
    node = SchedulerNode(proj, "step1", "0")
    os.makedirs(os.path.dirname(node.get_manifest(input=True)), exist_ok=True)
    os.makedirs(os.path.dirname(node.get_manifest(input=False)), exist_ok=True)
    
    proj.set('record', 'status', 'success', step='step1', index='0')
    proj.write_manifest(node.get_manifest(input=True))
    proj.write_manifest(node.get_manifest(input=False))
    
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    
    # Create new node - should not raise
    new_node = SchedulerNode(proj, "step1", "0")
    
    try:
        with new_node.runtime():
            new_node.requires_run()
        assert True
    except SchedulerNodeReset as e:
        # Should not raise for patch-related reasons
        assert "Patch" not in str(e)
