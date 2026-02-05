"""Tests for patch change detection in incremental builds."""
import os
import pytest
from siliconcompiler import Design, Project
from siliconcompiler.flowgraph import Flowgraph
from siliconcompiler.scheduler import Scheduler
from siliconcompiler.tools.builtin.nop import NOPTask
import difflib


@pytest.fixture
def design_with_patch(tmp_path):
    """Create a design with a single patch."""
    design = Design("testdesign")
    
    # Create test file
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    module_path = src_dir / "module.v"
    module_path.write_text("module test;\n  wire a;\nendmodule\n")
    
    design.set_dataroot("src", str(src_dir))
    
    with design.active_fileset("rtl"), design.active_dataroot("src"):
        design.set_topmodule("test")
        design.add_file("module.v")
        
        # Create patch
        original = "module test;\n  wire a;\nendmodule\n"
        modified = "module test;\n  wire a, b;\nendmodule\n"
        patch_text = ''.join(difflib.unified_diff(
            original.splitlines(keepends=True),
            modified.splitlines(keepends=True),
            fromfile='module.v',
            tofile='module.v'
        ))
        
        patch = design.get("fileset", "rtl", "patch", "fix1", field="schema")
        patch.set('file', 'module.v')
        patch.set('file', 'src', field='dataroot')
        patch.set('diff', patch_text)
    
    return design, module_path


@pytest.mark.skip(reason="Patch restoration on removal not yet implemented")
def test_patch_removed_triggers_rerun(design_with_patch, tmp_path, monkeypatch):
    """Test that removing a patch restores the original file."""
    from siliconcompiler.utils import curation
    import logging
    
    design, module_path = design_with_patch
    
    flow = Flowgraph("testflow")
    flow.node("step1", NOPTask())
    
    proj = Project(design)
    proj.set_flow(flow)
    proj.set("option", "fileset", "rtl")
    
    # Set up build directory
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    proj.set("option", "builddir", str(build_dir))
    proj.set("option", "jobname", "testjob")
    
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)
    
    scheduler = Scheduler(proj)
    
    # First run with patch
    scheduler._Scheduler__mark_patch_files_for_collection()
    curation.collect(proj, verbose=False)
    scheduler._Scheduler__apply_patches_after_collection()
    
    # Get the collected file
    from siliconcompiler.utils.paths import collectiondir
    coll_dir = collectiondir(proj)
    param = design.get('fileset', 'rtl', 'file', 'verilog', field=None)
    
    from siliconcompiler.schema.parametervalue import NodeListValue
    for node_val, _, _ in param.getvalues(return_values=False):
        if isinstance(node_val, NodeListValue):
            values_list = node_val.values
        else:
            values_list = [node_val]
        
        files = design.get('fileset', 'rtl', 'file', 'verilog')
        idx = files.index('module.v')
        value = values_list[idx]
        hashed = value.get_hashed_filename()
        file_path = os.path.join(coll_dir, hashed)
        orig_path = f"{file_path}.sc_orig_patch"
        
        # Verify patch was applied
        with open(file_path, "r") as f:
            content = f.read()
        assert "wire a, b;" in content
        
        # Verify .sc_orig_patch exists
        assert os.path.exists(orig_path)
        with open(orig_path, "r") as f:
            orig_content = f.read()
        assert "wire a;" in orig_content
        assert "wire a, b;" not in orig_content
        
        # Remove the patch from the design
        design.remove("fileset", "rtl", "patch", "fix1")
        
        # Mark for collection again - should restore .sc_orig_patch
        scheduler._Scheduler__mark_patch_files_for_collection()
        
        # The file should now be restored to original
        with open(file_path, "r") as f:
            restored_content = f.read()
        assert "wire a;" in restored_content
        assert "wire a, b;" not in restored_content, \
            "File should be restored when patch is removed"
        
        break


@pytest.mark.skip(reason="Patch restoration on removal not yet implemented")
def test_patch_removal_restores_original_file(design_with_patch, tmp_path, monkeypatch):
    """Test that removing a patch correctly restores the original file from .sc_orig_patch."""
    from siliconcompiler.utils import curation
    import logging
    
    design, module_path = design_with_patch
    
    flow = Flowgraph("testflow")
    flow.node("step1", NOPTask())
    
    proj = Project(design)
    proj.set_flow(flow)
    proj.set("option", "fileset", "rtl")
    
    # Set up build directory
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    proj.set("option", "builddir", str(build_dir))
    proj.set("option", "jobname", "testjob")
    
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)
    
    scheduler = Scheduler(proj)
    
    # Apply patch
    scheduler._Scheduler__mark_patch_files_for_collection()
    curation.collect(proj, verbose=False)
    scheduler._Scheduler__apply_patches_after_collection()
    
    # Get the collected file
    from siliconcompiler.utils.paths import collectiondir
    coll_dir = collectiondir(proj)
    param = design.get('fileset', 'rtl', 'file', 'verilog', field=None)
    
    from siliconcompiler.schema.parametervalue import NodeListValue
    for node_val, _, _ in param.getvalues(return_values=False):
        if isinstance(node_val, NodeListValue):
            values_list = node_val.values
        else:
            values_list = [node_val]
        
        files = design.get('fileset', 'rtl', 'file', 'verilog')
        idx = files.index('module.v')
        value = values_list[idx]
        hashed = value.get_hashed_filename()
        file_path = os.path.join(coll_dir, hashed)
        orig_path = f"{file_path}.sc_orig_patch"
        
        # Save patched content
        with open(file_path, "r") as f:
            patched_content = f.read()
        assert "wire a, b;" in patched_content
        
        # Save original content
        with open(orig_path, "r") as f:
            original_content = f.read()
        assert "wire a;" in original_content
        
        # Remove patch
        design.remove("fileset", "rtl", "patch", "fix1")
        
        # Mark for collection - should restore original
        scheduler._Scheduler__mark_patch_files_for_collection()
        
        # Verify restoration
        with open(file_path, "r") as f:
            restored = f.read()
        
        assert restored == original_content, \
            "File should be restored to exact original content when patch removed"
        assert "wire a, b;" not in restored
        
        # .sc_orig_patch should still exist for future use
        assert os.path.exists(orig_path)
        
        break
