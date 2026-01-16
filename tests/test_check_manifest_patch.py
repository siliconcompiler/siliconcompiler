"""Tests for check_manifest validation of patches."""
import os
import pytest

from siliconcompiler import Design, Project
from siliconcompiler.flowgraph import Flowgraph


def test_check_manifest_patch_missing_file():
    """Test that check_manifest fails when patch has no file field."""
    design = Design("testdesign")
    
    with design.active_fileset("rtl"):
        design.set_topmodule("top")
        design.add_file("module.v")
        
        # Create patch without file field
        patch = design.get("fileset", "rtl", "patch", "fix1", field="schema")
        patch.set('diff', '  line 1\n- old\n+ new\n')
    
    proj = Project(design)
    proj.set_flow(Flowgraph("test"))
    proj.set("option", "fileset", "rtl")
    
    assert not proj.check_manifest()


def test_check_manifest_patch_missing_diff():
    """Test that check_manifest fails when patch has no diff field."""
    design = Design("testdesign")
    
    with design.active_fileset("rtl"):
        design.set_topmodule("top")
        design.add_file("module.v")
        
        # Create patch without diff field
        patch = design.get("fileset", "rtl", "patch", "fix1", field="schema")
        patch.set('file', 'module.v')
    
    proj = Project(design)
    proj.set_flow(Flowgraph("test"))
    
    proj.set("option", "fileset", "rtl")
    
    assert not proj.check_manifest()


def test_check_manifest_patch_file_not_in_fileset(tmp_path):
    """Test that check_manifest fails when patch file is not in fileset."""
    design = Design("testdesign")
    
    # Create a real file
    test_file = tmp_path / "module.v"
    test_file.write_text("module test; endmodule")
    
    design.set_dataroot("test", str(tmp_path))
    
    with design.active_fileset("rtl"), design.active_dataroot("test"):
        design.set_topmodule("top")
        design.add_file("module.v")
        
        # Create patch for file not in fileset
        patch = design.get("fileset", "rtl", "patch", "fix1", field="schema")
        patch.set('file', 'nonexistent.v')
        patch.set('diff', '  line 1\n- old\n+ new\n')
    
    proj = Project(design)
    proj.set_flow(Flowgraph("test"))
    
    proj.set("option", "fileset", "rtl")
    
    assert not proj.check_manifest()


def test_check_manifest_patch_file_in_different_fileset(tmp_path):
    """Test that check_manifest fails when patch file is in different fileset."""
    design = Design("testdesign")
    
    # Create test files
    test_file1 = tmp_path / "rtl.v"
    test_file1.write_text("module rtl; endmodule")
    test_file2 = tmp_path / "tb.v"
    test_file2.write_text("module tb; endmodule")
    
    design.set_dataroot("test", str(tmp_path))
    
    with design.active_dataroot("test"):
        with design.active_fileset("rtl"):
            design.set_topmodule("top")
            design.add_file("rtl.v")
            
            # Create patch for file in different fileset
            patch = design.get("fileset", "rtl", "patch", "fix1", field="schema")
            patch.set('file', 'tb.v')
            patch.set('diff', '  line 1\n- old\n+ new\n')
        
        with design.active_fileset("testbench"):
            design.set_topmodule("tb")
            design.add_file("tb.v")
    
    proj = Project(design)
    proj.set_flow(Flowgraph("test"))
    
    proj.set("option", "fileset", "rtl")
    
    assert not proj.check_manifest()


def test_check_manifest_patch_with_dataroot(tmp_path):
    """Test that check_manifest succeeds when patch file is in correct dataroot."""
    design = Design("testdesign")
    
    # Create test file
    test_file = tmp_path / "module.v"
    test_file.write_text("module test; endmodule")
    
    design.set_dataroot("test", str(tmp_path))
    
    with design.active_fileset("rtl"), design.active_dataroot("test"):
        design.set_topmodule("top")
        design.add_file("module.v")
        
        # Create valid patch
        patch = design.get("fileset", "rtl", "patch", "fix1", field="schema")
        patch.set('file', 'module.v')
        patch.set('diff', '  line 1\n- old\n+ new\n')
    
    proj = Project(design)
    proj.set_flow(Flowgraph("test"))
    
    proj.set("option", "fileset", "rtl")
    
    assert proj.check_manifest()


def test_check_manifest_patch_valid(tmp_path):
    """Test that check_manifest succeeds with valid patch."""
    design = Design("testdesign")
    
    # Create test file
    test_file = tmp_path / "module.v"
    test_file.write_text("module test; endmodule")
    
    design.set_dataroot("test", str(tmp_path))
    
    with design.active_fileset("rtl"), design.active_dataroot("test"):
        design.set_topmodule("top")
        design.add_file("module.v")
        
        # Create valid patch
        patch = design.get("fileset", "rtl", "patch", "fix1", field="schema")
        patch.set('file', 'module.v')
        patch.set('diff', '  line 1\n- old\n+ new\n')
    
    proj = Project(design)
    proj.set_flow(Flowgraph("test"))
    
    proj.set("option", "fileset", "rtl")
    
    assert proj.check_manifest()


def test_check_manifest_patch_in_dependencies(tmp_path):
    """Test that check_manifest validates patches in dependency filesets."""
    # Create test files
    dep_file = tmp_path / "dep.v"
    dep_file.write_text("module dep; endmodule")
    main_file = tmp_path / "main.v"
    main_file.write_text("module main; endmodule")
    
    # Create dependency design with patch
    dep = Design("dep")
    dep.set_dataroot("deproot", str(tmp_path))
    
    with dep.active_fileset("rtl"), dep.active_dataroot("deproot"):
        dep.set_topmodule("dep_top")
        dep.add_file("dep.v")
        
        # Create patch with invalid file reference
        patch_dep = dep.get("fileset", "rtl", "patch", "dep_fix", field="schema")
        patch_dep.set('file', 'nonexistent.v')
        patch_dep.set('diff', '  line 1\n- old\n+ new\n')
    
    # Create main design
    design = Design("main")
    design.set_dataroot("mainroot", str(tmp_path))
    
    with design.active_fileset("rtl"), design.active_dataroot("mainroot"):
        design.set_topmodule("main_top")
        design.add_file("main.v")
        design.add_depfileset(dep, "rtl")
    
    proj = Project(design)
    proj.set_flow(Flowgraph("test"))
    
    proj.set("option", "fileset", "rtl")
    
    # Should fail because dependency has invalid patch
    assert not proj.check_manifest()


def test_check_manifest_multiple_patches(tmp_path):
    """Test check_manifest with multiple patches."""
    design = Design("testdesign")
    
    # Create test files
    file1 = tmp_path / "module1.v"
    file1.write_text("module test1; endmodule")
    file2 = tmp_path / "module2.v"
    file2.write_text("module test2; endmodule")
    
    design.set_dataroot("test", str(tmp_path))
    
    with design.active_fileset("rtl"), design.active_dataroot("test"):
        design.set_topmodule("top")
        design.add_file("module1.v")
        design.add_file("module2.v")
        
        # Valid patch
        patch1 = design.get("fileset", "rtl", "patch", "fix1", field="schema")
        patch1.set('file', 'module1.v')
        patch1.set('diff', '  line 1\n- old\n+ new\n')
        
        # Invalid patch (missing diff)
        patch2 = design.get("fileset", "rtl", "patch", "fix2", field="schema")
        patch2.set('file', 'module2.v')
    
    proj = Project(design)
    proj.set_flow(Flowgraph("test"))
    
    proj.set("option", "fileset", "rtl")
    
    # Should fail because one patch is invalid
    assert not proj.check_manifest()


def test_check_manifest_no_patches(tmp_path):
    """Test that check_manifest succeeds with no patches."""
    design = Design("testdesign")
    
    test_file = tmp_path / "module.v"
    test_file.write_text("module test; endmodule")
    
    design.set_dataroot("test", str(tmp_path))
    
    with design.active_fileset("rtl"), design.active_dataroot("test"):
        design.set_topmodule("top")
        design.add_file("module.v")
    
    proj = Project(design)
    proj.set_flow(Flowgraph("test"))
    
    proj.set("option", "fileset", "rtl")
    
    assert proj.check_manifest()


def test_check_manifest_patch_wrong_dataroot(tmp_path):
    """Test that check_manifest fails when patch dataroot doesn't match file's dataroot."""
    design = Design("testdesign")
    
    # Create test file
    test_file = tmp_path / "module.v"
    test_file.write_text("module test; endmodule")
    
    design.set_dataroot("dataroot1", str(tmp_path))
    design.set_dataroot("dataroot2", str(tmp_path))
    
    with design.active_fileset("rtl"), design.active_dataroot("dataroot1"):
        design.set_topmodule("top")
        design.add_file("module.v")
        
        # Create patch with wrong dataroot
        patch = design.get("fileset", "rtl", "patch", "fix1", field="schema")
        patch.set('file', 'module.v')
        patch.set('dataroot', 'dataroot2')  # File has dataroot1
        patch.set('diff', '  line 1\n- old\n+ new\n')
    
    proj = Project(design)
    proj.set_flow(Flowgraph("test"))
    proj.set("option", "fileset", "rtl")
    
    assert not proj.check_manifest()


def test_check_manifest_patch_nonexistent_dataroot(tmp_path):
    """Test that check_manifest fails when patch references nonexistent dataroot."""
    design = Design("testdesign")
    
    # Create test file
    test_file = tmp_path / "module.v"
    test_file.write_text("module test; endmodule")
    
    design.set_dataroot("test", str(tmp_path))
    
    with design.active_fileset("rtl"), design.active_dataroot("test"):
        design.set_topmodule("top")
        design.add_file("module.v")
        
        # Create patch with nonexistent dataroot
        patch = design.get("fileset", "rtl", "patch", "fix1", field="schema")
        patch.set('file', 'module.v')
        patch.set('dataroot', 'nonexistent')
        patch.set('diff', '  line 1\n- old\n+ new\n')
    
    proj = Project(design)
    proj.set_flow(Flowgraph("test"))
    proj.set("option", "fileset", "rtl")
    
    assert not proj.check_manifest()


def test_check_manifest_patch_matching_dataroot(tmp_path):
    """Test that check_manifest succeeds when patch dataroot matches file's dataroot."""
    design = Design("testdesign")
    
    # Create test file
    test_file = tmp_path / "module.v"
    test_file.write_text("module test; endmodule")
    
    design.set_dataroot("test", str(tmp_path))
    
    with design.active_fileset("rtl"), design.active_dataroot("test"):
        design.set_topmodule("top")
        design.add_file("module.v")
        
        # Create patch with matching dataroot
        patch = design.get("fileset", "rtl", "patch", "fix1", field="schema")
        patch.set('file', 'module.v')
        patch.set('dataroot', 'test')
        patch.set('diff', '  line 1\n- old\n+ new\n')
    
    proj = Project(design)
    proj.set_flow(Flowgraph("test"))
    proj.set("option", "fileset", "rtl")
    
    assert proj.check_manifest()


def test_check_manifest_patch_no_dataroot_with_file_dataroot(tmp_path):
    """Test that check_manifest succeeds when patch has no dataroot but file does."""
    design = Design("testdesign")
    
    # Create test file
    test_file = tmp_path / "module.v"
    test_file.write_text("module test; endmodule")
    
    design.set_dataroot("test", str(tmp_path))
    
    with design.active_fileset("rtl"), design.active_dataroot("test"):
        design.set_topmodule("top")
        design.add_file("module.v")
        
        # Create patch without specifying dataroot (should inherit from file)
        patch = design.get("fileset", "rtl", "patch", "fix1", field="schema")
        patch.set('file', 'module.v')
        patch.set('diff', '  line 1\n- old\n+ new\n')
    
    proj = Project(design)
    proj.set_flow(Flowgraph("test"))
    proj.set("option", "fileset", "rtl")
    
    assert proj.check_manifest()


def test_check_manifest_patch_file_no_dataroot(tmp_path):
    """Test that check_manifest succeeds when both patch and file have no dataroot."""
    design = Design("testdesign")
    
    with design.active_fileset("rtl"):
        design.set_topmodule("top")
        design.add_file("module.v")  # No dataroot
        
        # Create patch without dataroot
        patch = design.get("fileset", "rtl", "patch", "fix1", field="schema")
        patch.set('file', 'module.v')
        patch.set('diff', '  line 1\n- old\n+ new\n')
    
    proj = Project(design)
    proj.set_flow(Flowgraph("test"))
    proj.set("option", "fileset", "rtl")
    
    assert proj.check_manifest()
