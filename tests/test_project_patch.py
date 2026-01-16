"""Tests for project summary headers with patch support."""
import os
import pytest

from siliconcompiler import Design, Project
from siliconcompiler.schema_support.patch import Patch


def test_summary_headers_no_patches():
    """Test summary headers when no patches are present."""
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")
    
    proj = Project(design)
    proj.add_fileset("rtl")
    
    headers = proj._summary_headers()
    
    # Should not have a patches entry
    patch_headers = [h for h in headers if h[0] == "patches"]
    assert len(patch_headers) == 0


def test_summary_headers_single_patch():
    """Test summary headers with a single patch."""
    design = Design("testdesign")
    
    with design.active_fileset("rtl"):
        design.set_topmodule("top")
        patch = design.get("fileset", "rtl", "patch", "fix1", field="schema")
        patch.set('file', 'module.v')
        patch.set('diff', '  line 1\n- old\n+ new\n')
    
    proj = Project(design)
    proj.add_fileset("rtl")
    
    headers = proj._summary_headers()
    
    # Should have a patches entry
    patch_headers = [h for h in headers if h[0] == "patches"]
    assert len(patch_headers) == 1
    assert "testdesign/rtl/fix1" in patch_headers[0][1]


def test_summary_headers_multiple_patches():
    """Test summary headers with multiple patches in same fileset."""
    design = Design("testdesign")
    
    with design.active_fileset("rtl"):
        design.set_topmodule("top")
        
        patch1 = design.get("fileset", "rtl", "patch", "fix1", field="schema")
        patch1.set('file', 'module1.v')
        patch1.set('diff', '  line 1\n- old1\n+ new1\n')
        
        patch2 = design.get("fileset", "rtl", "patch", "fix2", field="schema")
        patch2.set('file', 'module2.v')
        patch2.set('diff', '  line 1\n- old2\n+ new2\n')
    
    proj = Project(design)
    proj.add_fileset("rtl")
    
    headers = proj._summary_headers()
    
    # Should have a patches entry with both patches
    patch_headers = [h for h in headers if h[0] == "patches"]
    assert len(patch_headers) == 1
    assert "testdesign/rtl/fix1" in patch_headers[0][1]
    assert "testdesign/rtl/fix2" in patch_headers[0][1]


def test_summary_headers_patches_multiple_filesets():
    """Test summary headers with patches in multiple filesets."""
    design = Design("testdesign")
    
    with design.active_fileset("rtl"):
        design.set_topmodule("top")
        patch1 = design.get("fileset", "rtl", "patch", "fix1", field="schema")
        patch1.set('file', 'rtl.v')
        patch1.set('diff', '  line 1\n- old\n+ new\n')
    
    with design.active_fileset("testbench"):
        design.set_topmodule("tb")
        patch2 = design.get("fileset", "testbench", "patch", "fix2", field="schema")
        patch2.set('file', 'tb.v')
        patch2.set('diff', '  line 1\n- old\n+ new\n')
    
    proj = Project(design)
    proj.add_fileset("rtl")
    proj.add_fileset("testbench")
    
    headers = proj._summary_headers()
    
    # Should have patches from both filesets
    patch_headers = [h for h in headers if h[0] == "patches"]
    assert len(patch_headers) == 1
    assert "testdesign/rtl/fix1" in patch_headers[0][1]
    assert "testdesign/testbench/fix2" in patch_headers[0][1]


def test_summary_headers_patches_with_dependencies():
    """Test summary headers with patches in dependency filesets."""
    dep = Design("dep")
    with dep.active_fileset("rtl"):
        dep.set_topmodule("dep_top")
        patch_dep = dep.get("fileset", "rtl", "patch", "dep_fix", field="schema")
        patch_dep.set('file', 'dep.v')
        patch_dep.set('diff', '  line 1\n- old\n+ new\n')
    
    design = Design("main")
    with design.active_fileset("rtl"):
        design.set_topmodule("main_top")
        design.add_depfileset(dep, "rtl")
        
        patch_main = design.get("fileset", "rtl", "patch", "main_fix", field="schema")
        patch_main.set('file', 'main.v')
        patch_main.set('diff', '  line 1\n- old\n+ new\n')
    
    proj = Project(design)
    proj.add_fileset("rtl")
    
    headers = proj._summary_headers()
    
    # Should have patches from both main and dependency
    patch_headers = [h for h in headers if h[0] == "patches"]
    assert len(patch_headers) == 1
    assert "main/rtl/main_fix" in patch_headers[0][1]
    assert "dep/rtl/dep_fix" in patch_headers[0][1]


def test_summary_headers_only_enabled_filesets():
    """Test that only patches from enabled filesets are shown."""
    design = Design("testdesign")
    
    with design.active_fileset("rtl"):
        design.set_topmodule("top")
        patch_rtl = design.get("fileset", "rtl", "patch", "fix_rtl", field="schema")
        patch_rtl.set('file', 'rtl.v')
        patch_rtl.set('diff', '  line 1\n- old\n+ new\n')
    
    with design.active_fileset("testbench"):
        design.set_topmodule("tb")
        patch_tb = design.get("fileset", "testbench", "patch", "fix_tb", field="schema")
        patch_tb.set('file', 'tb.v')
        patch_tb.set('diff', '  line 1\n- old\n+ new\n')
    
    proj = Project(design)
    # Only enable rtl fileset
    proj.add_fileset("rtl")
    
    headers = proj._summary_headers()
    
    # Should only have patch from rtl fileset
    patch_headers = [h for h in headers if h[0] == "patches"]
    assert len(patch_headers) == 1
    assert "testdesign/rtl/fix_rtl" in patch_headers[0][1]
    assert "testdesign/testbench/fix_tb" not in patch_headers[0][1]


def test_summary_headers_order():
    """Test that patches header appears in correct position."""
    design = Design("testdesign")
    
    with design.active_fileset("rtl"):
        design.set_topmodule("top")
        patch = design.get("fileset", "rtl", "patch", "fix1", field="schema")
        patch.set('file', 'module.v')
        patch.set('diff', '  line 1\n- old\n+ new\n')
    
    proj = Project(design)
    proj.add_fileset("rtl")
    
    headers = proj._summary_headers()
    header_keys = [h[0] for h in headers]
    
    # Patches should appear after filesets and before jobdir
    assert "design" in header_keys
    assert "filesets" in header_keys
    assert "patches" in header_keys
    assert "jobdir" in header_keys
    
    # Check order
    design_idx = header_keys.index("design")
    filesets_idx = header_keys.index("filesets")
    patches_idx = header_keys.index("patches")
    jobdir_idx = header_keys.index("jobdir")
    
    assert design_idx < filesets_idx < patches_idx < jobdir_idx
