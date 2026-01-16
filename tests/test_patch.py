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

    # Create a diff using ndiff format
    diff_text = "  line 1\n- line 2\n+ line two\n  line 3\n"

    # Create a Patch object and set the diff
    patch = Patch('testpatch')
    patch.set('diff', diff_text)

    # Apply the patch
    patch.apply(file_to_patch)

    # Check the patched file
    with open(file_to_patch, "r") as f:
        patched_content = f.read()

    expected_content = "line 1\nline two\nline 3\n"
    assert patched_content == expected_content

    # Check the backup file
    backup_file = f"{file_to_patch}.orig"
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
    patch.set('diff', "  line 1\n- line 2\n+ line two\n")
    
    # File doesn't exist, should raise FileNotFoundError
    with pytest.raises(FileNotFoundError, match="File to patch does not exist"):
        patch.apply("/nonexistent/file.txt")


def test_apply_patch_backup_failure(tmpdir, monkeypatch):
    """Test patch application when backup creation fails."""
    # Create a file to patch
    file_to_patch = os.path.join(tmpdir, "test.txt")
    with open(file_to_patch, "w") as f:
        f.write("line 1\nline 2\n")
    
    patch = Patch('testpatch')
    patch.set('diff', "  line 1\n- line 2\n+ line two\n")
    
    # Mock shutil.copy to raise an exception
    import shutil
    original_copy = shutil.copy
    def mock_copy(*args, **kwargs):
        raise PermissionError("Mocked permission error")
    
    monkeypatch.setattr(shutil, 'copy', mock_copy)
    
    # Should raise IOError
    with pytest.raises(IOError, match="Could not create backup"):
        patch.apply(file_to_patch)


def test_apply_patch_write_failure(tmpdir, monkeypatch):
    """Test patch application when writing patched file fails."""
    # Create a file to patch
    file_to_patch = os.path.join(tmpdir, "test.txt")
    with open(file_to_patch, "w") as f:
        f.write("line 1\nline 2\n")
    
    patch = Patch('testpatch')
    patch.set('diff', "  line 1\n- line 2\n+ line two\n")
    
    # Mock the file write to fail - we need to let backup succeed but file write fail
    original_open = open
    call_count = [0]  # Use list to avoid closure issues
    
    def mock_open(path, *args, **kwargs):
        if 'w' in str(args[0] if args else kwargs.get('mode', '')):
            # First write is backup (.orig), let it succeed
            # Second write is the actual patch file, make it fail
            call_count[0] += 1
            if call_count[0] == 2:
                raise PermissionError("Mocked write error")
        return original_open(path, *args, **kwargs)
    
    monkeypatch.setattr('builtins.open', mock_open)
    
    # Should raise IOError
    with pytest.raises(IOError, match="Could not write patched file"):
        patch.apply(file_to_patch)


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
    assert "  line 1" in diff_text
    assert "- line 2" in diff_text
    assert "+ line two" in diff_text
    assert "  line 3" in diff_text


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
    
    patch.apply(target_file)
    
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
    diff_text = "  line 1\n- line 2\n- line 3\n+ line two and three\n  line 4\n  line 5\n"

    patch = Patch('testpatch')
    patch.set('diff', diff_text)
    patch.apply(file_to_patch)

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
    diff_text = "+ new line\n"

    patch = Patch('testpatch')
    patch.set('diff', diff_text)
    patch.apply(file_to_patch)

    # Check the patched file
    with open(file_to_patch, "r") as f:
        patched_content = f.read()

    assert patched_content == "new line\n"
