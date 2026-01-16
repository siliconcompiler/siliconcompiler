"""Tests for design patch support in filesets."""
import os
import pytest

from siliconcompiler import Design
from siliconcompiler.schema_support.patch import Patch


def test_add_patch_to_fileset():
    """Test adding a patch to a fileset."""
    design = Design("test")
    
    with design.active_fileset("rtl"):
        # Get the patch schema and configure it
        patch = design.get("fileset", "rtl", "patch", "mypatch", field="schema")
        patch.set('file', 'test.v')
        patch.set('diff', '  line 1\n- line 2\n+ line two\n')
    
    # Verify the patch was added
    patch_keys = design.getkeys("fileset", "rtl", "patch")
    assert "mypatch" in patch_keys
    
    # Verify we can retrieve the patch
    retrieved_patch = design.get("fileset", "rtl", "patch", "mypatch", field="schema")
    assert retrieved_patch.get('file') == 'test.v'
    assert retrieved_patch.get('diff') == '  line 1\n- line 2\n+ line two\n'


def test_multiple_patches_in_fileset():
    """Test adding multiple patches to a fileset."""
    design = Design("test")
    
    with design.active_fileset("rtl"):
        # Add first patch
        patch1 = design.get("fileset", "rtl", "patch", "patch1", field="schema")
        patch1.set('file', 'module1.v')
        patch1.set('diff', '  line 1\n- old\n+ new\n')
        
        # Add second patch
        patch2 = design.get("fileset", "rtl", "patch", "patch2", field="schema")
        patch2.set('file', 'module2.v')
        patch2.set('diff', '  line 1\n- old2\n+ new2\n')
    
    # Verify both patches exist
    patch_keys = design.getkeys("fileset", "rtl", "patch")
    assert "patch1" in patch_keys
    assert "patch2" in patch_keys
    assert len(patch_keys) == 2


def test_patches_in_different_filesets():
    """Test patches in different filesets are independent."""
    design = Design("test")
    
    with design.active_fileset("rtl"):
        patch_rtl = design.get("fileset", "rtl", "patch", "rtl_patch", field="schema")
        patch_rtl.set('file', 'rtl.v')
    
    with design.active_fileset("testbench"):
        patch_tb = design.get("fileset", "testbench", "patch", "tb_patch", field="schema")
        patch_tb.set('file', 'tb.v')
    
    # Verify patches are in correct filesets
    rtl_patches = design.getkeys("fileset", "rtl", "patch")
    tb_patches = design.getkeys("fileset", "testbench", "patch")
    
    assert "rtl_patch" in rtl_patches
    assert "rtl_patch" not in tb_patches
    assert "tb_patch" in tb_patches
    assert "tb_patch" not in rtl_patches


def test_patch_with_dataroot():
    """Test patch with dataroot field."""
    design = Design("test")
    
    with design.active_fileset("rtl"):
        patch = design.get("fileset", "rtl", "patch", "mypatch", field="schema")
        patch.set('file', 'test.v')
        patch.set('dataroot', '/path/to/fileset')
        patch.set('diff', '  line 1\n- old\n+ new\n')
    
    retrieved_patch = design.get("fileset", "rtl", "patch", "mypatch", field="schema")
    assert retrieved_patch.get('dataroot') == '/path/to/fileset'


def test_empty_patch_name():
    """Test that patches can have default names."""
    design = Design("test")
    
    with design.active_fileset("rtl"):
        patch = design.get("fileset", "rtl", "patch", "unnamed", field="schema")
        patch.set('file', 'test.v')
        patch.set('diff', '  line 1\n- old\n+ new\n')
    
    # Should still be retrievable
    retrieved_patch = design.get("fileset", "rtl", "patch", "unnamed", field="schema")
    assert retrieved_patch.get('file') == 'test.v'


def test_copy_fileset_with_patches():
    """Test that patches are copied when copying filesets."""
    design = Design("test")
    
    with design.active_fileset("rtl"):
        patch = design.get("fileset", "rtl", "patch", "mypatch", field="schema")
        patch.set('file', 'test.v')
        patch.set('diff', '  line 1\n- old\n+ new\n')
    
    # Copy the fileset
    design.copy_fileset("rtl", "rtl_copy")
    
    # Verify patch was copied
    patch_keys = design.getkeys("fileset", "rtl_copy", "patch")
    assert "mypatch" in patch_keys
    
    # Verify the copied patch has the same data
    copied_patch = design.get("fileset", "rtl_copy", "patch", "mypatch", field="schema")
    assert copied_patch.get('file') == 'test.v'
    assert copied_patch.get('diff') == '  line 1\n- old\n+ new\n'


def test_patch_in_dependency():
    """Test that patches can exist in dependency filesets."""
    dep = Design("dep")
    with dep.active_fileset("rtl"):
        patch = dep.get("fileset", "rtl", "patch", "dep_patch", field="schema")
        patch.set('file', 'dep.v')
        patch.set('diff', '  line 1\n- old\n+ new\n')
    
    design = Design("main")
    design.add_dep(dep)
    
    # Verify we can access patches from dependency
    dep_obj = design.get_dep("dep")
    patch_keys = dep_obj.getkeys("fileset", "rtl", "patch")
    assert "dep_patch" in patch_keys
