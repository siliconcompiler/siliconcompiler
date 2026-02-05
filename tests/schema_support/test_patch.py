import os
import pytest

from siliconcompiler.schema_support.patch import Patch


def test_patch_init():
    """Test patch initialization."""
    patch = Patch('testpatch')
    assert patch.name == 'testpatch'
    
    # Test with no name
    patch_noname = Patch()
    assert patch_noname.name is None


def test_patch_schema():
    """Test patch schema fields."""
    patch = Patch('testpatch')
    
    # Test file field
    patch.set('file', 'test.txt')
    assert patch.get('file') == 'test.txt'
    
    # Test diff field
    diff_text = "- old line\n+ new line\n"
    patch.set('diff', diff_text)
    assert patch.get('diff') == diff_text


def test_apply_patch_success(tmpdir):
    """Test successful patch application."""
    # Create a file to patch
    file_content = "line 1\nline 2\nline 3\n"
    file_to_patch = os.path.join(tmpdir, "test.txt")
    with open(file_to_patch, "w") as f:
        f.write(file_content)

    # Create a diff using unified_diff format
    diff_text = "--- a/test.txt\n+++ b/test.txt\n@@ -1,3 +1,3 @@\n line 1\n-line 2\n+line two\n line 3\n"

    # Create a Patch object and set the diff
    patch = Patch('testpatch')
    patch.set('file', file_to_patch)
    patch.set('diff', diff_text)

    # Apply the patch
    patch.apply()

    # Check the patched file
    with open(file_to_patch, "r") as f:
        patched_content = f.read()

    expected_content = "line 1\nline two\nline 3\n"
    assert patched_content == expected_content

    # Check the backup file
    backup_file = f"{file_to_patch}.sc_orig_patch"
    assert os.path.exists(backup_file)
    with open(backup_file, "r") as f:
        backup_content = f.read()
    assert backup_content == file_content


def test_apply_patch_no_diff():
    """Test patch application with no diff text."""
    patch = Patch('testpatch')
    
    # No diff set, should raise ValueError
    with pytest.raises(ValueError, match="No diff text found"):
        patch.apply("/some/file.txt")


def test_apply_patch_file_not_found():
    """Test patch application when file doesn't exist."""
    patch = Patch('testpatch')
    patch.set('file', '/nonexistent/file.txt')
    patch.set('diff', "--- a/file.txt\n+++ b/file.txt\n@@ -1,2 +1,2 @@\n line 1\n-line 2\n+line two\n")
    
    # File doesn't exist, should raise FileNotFoundError
    with pytest.raises(FileNotFoundError, match="Could not find"):
        patch.apply()


def test_apply_patch_backup_failure(tmpdir, monkeypatch):
    """Test patch application when backup creation fails."""
    # Create a file to patch
    file_to_patch = os.path.join(tmpdir, "test.txt")
    with open(file_to_patch, "w") as f:
        f.write("line 1\nline 2\n")
    
    patch = Patch('testpatch')
    patch.set('file', file_to_patch)
    patch.set('diff', "--- a/test.txt\n+++ b/test.txt\n@@ -1,2 +1,2 @@\n line 1\n-line 2\n+line two\n")
    
    # Mock shutil.copy2 to raise an exception
    import shutil
    original_copy2 = shutil.copy2
    def mock_copy2(*args, **kwargs):
        raise PermissionError("Mocked permission error")
    
    monkeypatch.setattr(shutil, 'copy2', mock_copy2)
    
    # Should raise IOError
    with pytest.raises(IOError, match="Could not create backup"):
        patch.apply()


def test_apply_patch_write_failure(tmpdir, monkeypatch):
    """Test patch application when writing patched file fails."""
    # Create a file to patch
    file_to_patch = os.path.join(tmpdir, "test.txt")
    with open(file_to_patch, "w") as f:
        f.write("line 1\nline 2\n")
    
    patch = Patch('testpatch')
    patch.set('file', file_to_patch)
    patch.set('diff', "--- a/test.txt\n+++ b/test.txt\n@@ -1,2 +1,2 @@\n line 1\n-line 2\n+line two\n")
    
    # Mock the file write to fail - we need to let backup succeed but file write fail
    original_open = open
    call_count = [0]  # Use list to avoid closure issues
    
    def mock_open(path, *args, **kwargs):
        if 'w' in str(args[0] if args else kwargs.get('mode', '')):
            # First write is backup (.sc_orig_patch), let it succeed
            # Second write is the actual patch file, make it fail
            call_count[0] += 1
            if call_count[0] == 2:
                raise PermissionError("Mocked write error")
        return original_open(path, *args, **kwargs)
    
    monkeypatch.setattr('builtins.open', mock_open)
    
    # Should raise IOError
    with pytest.raises(IOError, match="Could not write patched file"):
        patch.apply()


def test_create_from_files(tmpdir):
    """Test creating a diff from two files."""
    # Create original file
    original_file = os.path.join(tmpdir, "original.txt")
    with open(original_file, "w") as f:
        f.write("line 1\nline 2\nline 3\n")
    
    # Create modified file
    modified_file = os.path.join(tmpdir, "modified.txt")
    with open(modified_file, "w") as f:
        f.write("line 1\nline two\nline 3\n")
    
    # Create patch and generate diff
    patch = Patch('testpatch')
    patch.create_from_files(original_file, modified_file)
    
    # Verify diff was set and contains expected markers
    diff_text = patch.get('diff')
    assert " line 1" in diff_text
    assert "-line 2" in diff_text
    assert "+line two" in diff_text
    assert " line 3" in diff_text


def test_create_from_files_and_apply(tmpdir):
    """Test creating a diff and applying it."""
    # Create original file
    original_file = os.path.join(tmpdir, "original.txt")
    original_content = "line 1\nline 2\nline 3\n"
    with open(original_file, "w") as f:
        f.write(original_content)
    
    # Create modified file
    modified_file = os.path.join(tmpdir, "modified.txt")
    modified_content = "line 1\nline two\nline 3\nline 4\n"
    with open(modified_file, "w") as f:
        f.write(modified_content)
    
    # Create patch and generate diff from files
    patch = Patch('testpatch')
    patch.create_from_files(original_file, modified_file)
    
    # Apply the diff to a copy of the original file
    target_file = os.path.join(tmpdir, "target.txt")
    with open(target_file, "w") as f:
        f.write(original_content)
    
    patch.set('file', target_file)
    patch.apply()
    
    # Verify the result matches the modified file
    with open(target_file, "r") as f:
        result_content = f.read()
    
    assert result_content == modified_content


def test_apply_patch_multiline_change(tmpdir):
    """Test patch with multiple line changes."""
    # Create a file to patch
    file_content = "line 1\nline 2\nline 3\nline 4\nline 5\n"
    file_to_patch = os.path.join(tmpdir, "test.txt")
    with open(file_to_patch, "w") as f:
        f.write(file_content)

    # Create a diff with multiple changes
    diff_text = "--- a/test.txt\n+++ b/test.txt\n@@ -1,5 +1,4 @@\n line 1\n-line 2\n-line 3\n+line two and three\n line 4\n line 5\n"

    patch = Patch('testpatch')
    patch.set('file', file_to_patch)
    patch.set('diff', diff_text)
    patch.apply()

    # Check the patched file
    with open(file_to_patch, "r") as f:
        patched_content = f.read()

    expected_content = "line 1\nline two and three\nline 4\nline 5\n"
    assert patched_content == expected_content


def test_apply_patch_empty_file(tmpdir):
    """Test patch on empty file."""
    # Create an empty file
    file_to_patch = os.path.join(tmpdir, "empty.txt")
    with open(file_to_patch, "w") as f:
        f.write("")

    # Create a diff adding content
    diff_text = "--- a/empty.txt\n+++ b/empty.txt\n@@ -0,0 +1 @@\n+new line\n"

    patch = Patch('testpatch')
    patch.set('file', file_to_patch)
    patch.set('diff', diff_text)
    patch.apply()

    # Check the patched file
    with open(file_to_patch, "r") as f:
        patched_content = f.read()

    assert patched_content == "new line\n"


def test_patch_spi_file(tmpdir):
    """Test applying a patch to the SPI Verilog file - real bug fix."""
    import difflib
    
    # Create a copy of the buggy SPI file
    spi_content_buggy = """module spi(
  input clk,
  input rst,
  input ss,
  input mosi,
  output miso,
  input sck,
  output [7:0] dout,
  output done
);
 
  reg ss_d, ss_q;
  reg mosi_d, mosi_q;
  reg sck_d, sck_q;
  reg sck_old_d, sck_old_q;
  reg [7:0] data_d, data_q;
  reg done_d, done_q;
  reg [2:0] bit_ct_d, bit_ct_q;
  reg [7:0] dout_d, dout_q;
  reg miso_d, miso_q;
 
  assign miso = miso_q;
  assign done = ~done_q; // This should have been done_q
  assign dout = dout_q;
 
  always @(*) begin
    ss_d = ss;
  end
endmodule
"""
    
    spi_content_fixed = """module spi(
  input clk,
  input rst,
  input ss,
  input mosi,
  output miso,
  input sck,
  output [7:0] dout,
  output done
);
 
  reg ss_d, ss_q;
  reg mosi_d, mosi_q;
  reg sck_d, sck_q;
  reg sck_old_d, sck_old_q;
  reg [7:0] data_d, data_q;
  reg done_d, done_q;
  reg [2:0] bit_ct_d, bit_ct_q;
  reg [7:0] dout_d, dout_q;
  reg miso_d, miso_q;
 
  assign miso = miso_q;
  assign done = done_q;
  assign dout = dout_q;
 
  always @(*) begin
    ss_d = ss;
  end
endmodule
"""
    
    spi_file = os.path.join(tmpdir, "spi.v")
    with open(spi_file, "w") as f:
        f.write(spi_content_buggy)
    
    # Generate the patch using difflib to ensure correct format
    patch_text = ''.join(difflib.unified_diff(
        spi_content_buggy.splitlines(keepends=True),
        spi_content_fixed.splitlines(keepends=True),
        fromfile='spi.v',
        tofile='spi.v'
    ))
    
    patch = Patch('spi_fix')
    patch.set('file', spi_file)
    patch.set('diff', patch_text)
    
    # Apply the patch
    patch.apply()
    
    # Verify the patch was applied
    with open(spi_file, "r") as f:
        patched_content = f.read()
    
    # Check that the bug fix was applied
    assert "assign done = done_q;" in patched_content
    assert "assign done = ~done_q;" not in patched_content
    # The comment should be removed
    assert "// This should have been done_q" not in patched_content


def test_patch_with_tabs(tmpdir):
    """Test that patches handle tabs in the header correctly."""
    original_content = "line1\nline2\nline3\n"
    
    test_file = os.path.join(tmpdir, "test.txt")
    with open(test_file, "w") as f:
        f.write(original_content)
    
    # Patch with tab character in header (like from diff command)
    patch_text = "--- test.txt\t2026-01-17 10:12:34\n+++ test_new.txt\t2026-01-17 10:12:49\n@@ -1,3 +1,3 @@\n line1\n-line2\n+line TWO\n line3\n"
    
    patch = Patch('tab_test')
    patch.set('file', test_file)
    patch.set('diff', patch_text)
    patch.apply()
    
    with open(test_file, "r") as f:
        result = f.read()
    
    assert result == "line1\nline TWO\nline3\n"


def test_patch_multiline_context(tmpdir):
    """Test patch with multiple lines of context."""
    original_content = """line 1
line 2
line 3
line 4
line 5
line 6
line 7
"""
    
    test_file = os.path.join(tmpdir, "test.txt")
    with open(test_file, "w") as f:
        f.write(original_content)
    
    # Patch with more context
    patch_text = """--- test.txt
+++ test.txt
@@ -2,5 +2,5 @@
 line 2
 line 3
-line 4
+line FOUR
 line 5
 line 6
"""
    
    patch = Patch('context_test')
    patch.set('file', test_file)
    patch.set('diff', patch_text)
    patch.apply()
    
    with open(test_file, "r") as f:
        result = f.read()
    
    expected = """line 1
line 2
line 3
line FOUR
line 5
line 6
line 7
"""
    assert result == expected


def test_patch_multiple_hunks(tmpdir):
    """Test patch with multiple separate hunks."""
    original_content = """line 1
line 2
line 3
line 4
line 5
line 6
line 7
line 8
line 9
line 10
"""
    
    test_file = os.path.join(tmpdir, "test.txt")
    with open(test_file, "w") as f:
        f.write(original_content)
    
    # Patch with two separate hunks
    patch_text = """--- test.txt
+++ test.txt
@@ -1,3 +1,3 @@
 line 1
-line 2
+line TWO
 line 3
@@ -8,3 +8,3 @@
 line 8
-line 9
+line NINE
 line 10
"""
    
    patch = Patch('multi_hunk')
    patch.set('file', test_file)
    patch.set('diff', patch_text)
    patch.apply()
    
    with open(test_file, "r") as f:
        result = f.read()
    
    expected = """line 1
line TWO
line 3
line 4
line 5
line 6
line 7
line 8
line NINE
line 10
"""
    assert result == expected
