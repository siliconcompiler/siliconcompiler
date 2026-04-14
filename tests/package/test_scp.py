"""
Comprehensive test suite for SCPResolver.

This module tests the SCP package resolver with complete coverage, ensuring:
- subprocess.run is always mocked (never invoked directly)
- Cache behavior works correctly
- Error handling is robust
- URL parsing and command construction are correct
- Various edge cases are handled properly
"""
import pytest
import os
import os.path
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

from siliconcompiler.package.scp import SCPResolver
from siliconcompiler import Project


# ============================================================================
# Initialization Tests
# ============================================================================

def test_init_basic():
    """Test basic initialization with standard arguments."""
    resolver = SCPResolver("testscp", Project(),
                           "scp://github.com/test_owner/test_repo", "v1.0")
    assert resolver.host == "github.com"
    assert resolver.host_path == "/test_owner/test_repo"
    assert resolver.host_port is None


def test_init_with_different_host():
    """Test initialization with different hosts."""
    resolver = SCPResolver("testscp", Project(),
                           "scp://example.com/path/to/repo", "v2.0")
    assert resolver.host == "example.com"
    assert resolver.host_path == "/path/to/repo"
    assert resolver.host_port is None


def test_init_with_complex_path():
    """Test initialization with complex paths."""
    resolver = SCPResolver("testscp", Project(),
                           "scp://server.org/deep/nested/path/repo", "main")
    assert resolver.host == "server.org"
    assert resolver.host_path == "/deep/nested/path/repo"
    assert resolver.host_port is None


def test_init_with_port_in_url():
    """Test initialization with port number in URL."""
    resolver = SCPResolver("testscp", Project(),
                           "scp://github.com:2222/test_owner/test_repo", "v1.0")
    assert resolver.host == "github.com"
    assert resolver.host_path == "/test_owner/test_repo"
    assert resolver.host_port == 2222


# ============================================================================
# Cache Checking Tests
# ============================================================================
def test_check_cache_exists(tmp_path):
    """Test that check_cache returns True when cache directory exists."""
    proj = Project("testproj")
    proj.option.set_cachedir(tmp_path)

    resolver = SCPResolver("testscp", proj, "scp://github.com/test_owner/test_repo", "v1.0")
    # Create the cache directory
    os.makedirs(resolver.cache_path, exist_ok=True)

    assert resolver.check_cache() is True


def test_check_cache_not_exists(tmp_path):
    """Test that check_cache returns False when cache directory does not exist."""
    proj = Project("testproj")
    proj.option.set_cachedir(tmp_path)

    resolver = SCPResolver("testscp", proj, "scp://github.com/test_owner/test_repo", "v1.0")

    assert resolver.check_cache() is False


def test_check_cache_with_cached_files(tmp_path):
    """Test that check_cache returns True with actual cached content."""
    proj = Project("testproj")
    proj.option.set_cachedir(tmp_path)

    resolver = SCPResolver("testscp", proj, "scp://github.com/test_owner/test_repo", "v1.0")
    # Create cache directory with some content
    os.makedirs(resolver.cache_path, exist_ok=True)
    (Path(resolver.cache_path) / "dummy_file.txt").write_text("test content")

    assert resolver.check_cache() is True


# ============================================================================
# Remote Resolution Tests
# ============================================================================

@patch("siliconcompiler.package.scp.subprocess.run")
@patch("siliconcompiler.package.scp.shutil.which")
def test_resolve_remote_success(mock_which, mock_run, tmp_path):
    """Test successful SCP transfer."""
    proj = Project("testproj")
    proj.option.set_cachedir(tmp_path)

    resolver = SCPResolver("testscp", proj, "scp://github.com/test_owner/test_repo", "v1.0")
    mock_which.return_value = "/usr/bin/scp"
    mock_run.return_value = MagicMock(returncode=0)

    resolver.resolve_remote()

    mock_which.assert_called_once_with("scp")
    mock_run.assert_called_once()
    args, _ = mock_run.call_args
    command = args[0]
    assert command[0] == "/usr/bin/scp"
    assert command[1] == "-C"  # compression flag
    assert command[2] == "-r"  # recursive flag
    assert command[3] == "github.com:/test_owner/test_repo"
    assert str(command[4]) == str(resolver.cache_path)


@patch("siliconcompiler.package.scp.subprocess.run")
@patch("siliconcompiler.package.scp.shutil.which")
def test_resolve_remote_scp_not_found(mock_which, mock_run, tmp_path):
    """Test error when SCP command is not available."""
    proj = Project("testproj")
    proj.option.set_cachedir(tmp_path)

    resolver = SCPResolver("testscp", proj, "scp://github.com/test_owner/test_repo", "v1.0")
    mock_which.return_value = None

    with pytest.raises(RuntimeError, match=r"^SCP command not found\. "
                                           r"Please ensure SCP is installed and in your PATH\.$"):
        resolver.resolve_remote()

    mock_run.assert_not_called()


@patch("siliconcompiler.package.scp.subprocess.run")
@patch("siliconcompiler.package.scp.shutil.which")
def test_resolve_remote_subprocess_fails(mock_which, mock_run, tmp_path):
    """Test error handling when subprocess returns non-zero exit code."""
    proj = Project("testproj")
    proj.option.set_cachedir(tmp_path)

    resolver = SCPResolver("testscp", proj, "scp://github.com/test_owner/test_repo", "v1.0")
    mock_which.return_value = "/usr/bin/scp"
    mock_run.return_value = MagicMock(
        returncode=1,
        stdout="Connection refused\n",
        stderr="Permission denied\n"
    )

    with pytest.raises(FileNotFoundError, match=r"^Failed to fetch data from .* using SCP\.$"):
        resolver.resolve_remote()

    mock_run.assert_called_once()


@patch("siliconcompiler.package.scp.subprocess.run")
@patch("siliconcompiler.package.scp.shutil.which")
def test_resolve_remote_subprocess_error_with_logging(mock_which, mock_run, tmp_path):
    """Test that errors from stdout/stderr trigger appropriate error handling."""
    proj = Project("testproj")
    proj.option.set_cachedir(tmp_path)

    resolver = SCPResolver("testscp", proj, "scp://github.com/test_owner/test_repo", "v1.0")
    mock_which.return_value = "/usr/bin/scp"
    mock_run.return_value = MagicMock(
        returncode=255,
        stdout="stdout error message\n",
        stderr="stderr error message\n"
    )

    # Verify that FileNotFoundError is raised when subprocess fails
    with pytest.raises(FileNotFoundError, match=r"^Failed to fetch data from .* using SCP\.$"):
        resolver.resolve_remote()

    # Verify subprocess.run was called
    mock_run.assert_called_once()


@patch("siliconcompiler.package.scp.SCPResolver.logger", new_callable=lambda: MagicMock())
@patch("siliconcompiler.package.scp.subprocess.run")
@patch("siliconcompiler.package.scp.shutil.which")
def test_resolve_remote_logs_stdout_stderr_on_error(mock_which, mock_run, mock_logger, tmp_path):
    """Test that stdout and stderr are correctly sent to logger when subprocess fails."""
    proj = Project("testproj")
    proj.option.set_cachedir(tmp_path)

    resolver = SCPResolver("testscp", proj, "scp://github.com/test_owner/test_repo", "v1.0")
    mock_which.return_value = "/usr/bin/scp"
    mock_run.return_value = MagicMock(
        returncode=255,
        stdout="error line 1\nerror line 2\n",
        stderr="stderr line 1\nstderr line 2\n"
    )
    resolver.logger = mock_logger

    # Verify that FileNotFoundError is raised when subprocess fails
    with pytest.raises(FileNotFoundError):
        resolver.resolve_remote()

    # Verify logger.error was called for each stdout and stderr line
    expected_calls = [
        ("error line 1",),
        ("error line 2",),
        ("stderr line 1",),
        ("stderr line 2",),
    ]
    actual_calls = [call[0] for call in mock_logger.error.call_args_list]
    assert actual_calls == expected_calls


@patch("siliconcompiler.package.scp.subprocess.run")
@patch("siliconcompiler.package.scp.shutil.which")
def test_resolve_remote_creates_cache_dir(mock_which, mock_run, tmp_path):
    """Test that resolve_remote works even if cache directory doesn't exist yet."""
    proj = Project("testproj")
    proj.option.set_cachedir(tmp_path)

    resolver = SCPResolver("testscp", proj, "scp://github.com/test_owner/test_repo", "v1.0")
    mock_which.return_value = "/usr/bin/scp"
    mock_run.return_value = MagicMock(returncode=0)

    # Ensure cache directory doesn't exist
    assert not os.path.exists(resolver.cache_path)

    resolver.resolve_remote()

    mock_run.assert_called_once()


# ============================================================================
# Full Resolve Workflow Tests
# ============================================================================

@patch("siliconcompiler.package.scp.subprocess.run")
@patch("siliconcompiler.package.scp.shutil.which")
def test_resolve_with_no_cache(mock_which, mock_run, tmp_path):
    """Test resolve() when cache doesn't exist (should fetch from remote)."""
    proj = Project("testproj")
    proj.option.set_cachedir(tmp_path)

    resolver = SCPResolver("testscp", proj, "scp://github.com/test_owner/test_repo", "v1.0")
    mock_which.return_value = "/usr/bin/scp"
    mock_run.return_value = MagicMock(returncode=0)

    result = resolver.resolve()

    assert isinstance(result, Path)
    assert "testscp-v1.0" in str(result)
    mock_run.assert_called_once()


@patch("siliconcompiler.package.scp.subprocess.run")
@patch("siliconcompiler.package.scp.shutil.which")
def test_resolve_with_cached_data(mock_which, mock_run, tmp_path):
    """Test resolve() when cache exists (should not fetch from remote)."""
    proj = Project("testproj")
    proj.option.set_cachedir(tmp_path)

    resolver = SCPResolver("testscp", proj, "scp://github.com/test_owner/test_repo", "v1.0")

    # Pre-populate the cache
    os.makedirs(resolver.cache_path, exist_ok=True)
    (Path(resolver.cache_path) / "cached_file.txt").write_text("cached content")

    result = resolver.resolve()

    assert isinstance(result, Path)
    # subprocess.run should NOT be called when cache exists
    mock_run.assert_not_called()
    mock_which.assert_not_called()


@patch("siliconcompiler.package.scp.subprocess.run")
@patch("siliconcompiler.package.scp.shutil.which")
def test_resolve_returns_correct_path(mock_which, mock_run, tmp_path):
    """Test that resolve() returns the correct cache path."""
    proj = Project("testproj")
    proj.option.set_cachedir(tmp_path)

    resolver = SCPResolver("testscp", proj, "scp://github.com/test_owner/test_repo", "v1.0")
    mock_which.return_value = "/usr/bin/scp"
    mock_run.return_value = MagicMock(returncode=0)

    result = resolver.resolve()

    # The result should be the exact cache path
    assert result == resolver.cache_path


# ============================================================================
# Edge Cases and Special Scenarios
# ============================================================================

@patch("siliconcompiler.package.scp.subprocess.run")
@patch("siliconcompiler.package.scp.shutil.which")
def test_resolve_with_special_characters_in_path(mock_which, mock_run, tmp_path):
    """Test SCP with special characters in path."""
    proj = Project("testproj")
    proj.option.set_cachedir(tmp_path)

    resolver = SCPResolver("testscp", proj,
                           "scp://github.com/test-owner/test_repo-v2", "v1.0")
    mock_which.return_value = "/usr/bin/scp"
    mock_run.return_value = MagicMock(returncode=0)

    resolver.resolve_remote()

    args, _ = mock_run.call_args
    command = args[0]
    assert command[3] == "github.com:/test-owner/test_repo-v2"


@patch("siliconcompiler.package.scp.subprocess.run")
@patch("siliconcompiler.package.scp.shutil.which")
def test_subprocess_never_executed_directly(mock_which, mock_run, tmp_path):
    """Verify that subprocess.run is always called via mock, never directly."""
    proj = Project("testproj")
    proj.option.set_cachedir(tmp_path)

    resolver = SCPResolver("testscp", proj, "scp://github.com/test_owner/test_repo", "v1.0")
    mock_which.return_value = "/usr/bin/scp"
    mock_run.return_value = MagicMock(returncode=0)

    # This should use mocked subprocess.run
    resolver.resolve_remote()

    # Verify mock was called
    assert mock_run.called
    # Verify it's still the mock (not actual subprocess)
    assert isinstance(mock_run, MagicMock)


@patch("siliconcompiler.package.scp.subprocess.run")
@patch("siliconcompiler.package.scp.shutil.which")
def test_different_references(mock_which, mock_run, tmp_path):
    """Test that different references result in different cache paths."""
    proj = Project("testproj")
    proj.option.set_cachedir(tmp_path)

    resolver_v1 = SCPResolver("testscp", proj, "scp://github.com/test_owner/test_repo", "v1.0")
    resolver_v2 = SCPResolver("testscp", proj, "scp://github.com/test_owner/test_repo", "v2.0")

    path_v1 = resolver_v1.cache_path
    path_v2 = resolver_v2.cache_path

    # Different references should have different cache paths
    assert path_v1 != path_v2


@patch("siliconcompiler.package.scp.subprocess.run")
@patch("siliconcompiler.package.scp.shutil.which")
def test_command_construction_correctness(mock_which, mock_run, tmp_path):
    """Test that the SCP command is constructed correctly."""
    proj = Project("testproj")
    proj.option.set_cachedir(tmp_path)

    resolver = SCPResolver("testscp", proj, "scp://github.com/test_owner/test_repo", "v1.0")
    mock_which.return_value = "/usr/bin/scp"
    mock_run.return_value = MagicMock(returncode=0)

    resolver.resolve_remote()

    args, _ = mock_run.call_args
    command = args[0]

    # Verify command structure and exact values
    assert len(command) == 5
    assert command[0] == "/usr/bin/scp"
    assert command[1] == "-C"
    assert command[2] == "-r"
    assert command[3] == "github.com:/test_owner/test_repo"
    assert str(command[4]) == str(resolver.cache_path)


@patch("siliconcompiler.package.scp.subprocess.run")
@patch("siliconcompiler.package.scp.shutil.which")
def test_subprocess_receives_correct_kwargs(mock_which, mock_run, tmp_path):
    """Test that subprocess.run receives the correct keyword arguments."""
    proj = Project("testproj")
    proj.option.set_cachedir(tmp_path)

    resolver = SCPResolver("testscp", proj, "scp://github.com/test_owner/test_repo", "v1.0")
    mock_which.return_value = "/usr/bin/scp"
    mock_run.return_value = MagicMock(returncode=0)

    resolver.resolve_remote()

    _, kwargs = mock_run.call_args
    # Check that stdout and stderr are captured exactly
    assert kwargs == {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "text": True}


# ============================================================================
# Port Handling Tests
# ============================================================================

@patch("siliconcompiler.package.scp.subprocess.run")
@patch("siliconcompiler.package.scp.shutil.which")
def test_command_with_default_port(mock_which, mock_run, tmp_path):
    """Test that default port (22) does not add -P flag to command."""
    proj = Project("testproj")
    proj.option.set_cachedir(tmp_path)

    resolver = SCPResolver("testscp", proj, "scp://github.com/test_owner/test_repo", "v1.0")
    mock_which.return_value = "/usr/bin/scp"
    mock_run.return_value = MagicMock(returncode=0)

    resolver.resolve_remote()

    args, _ = mock_run.call_args
    command = args[0]

    # Verify no -P flag for default port
    assert "-P" not in command
    assert command[3] == "github.com:/test_owner/test_repo"


@patch("siliconcompiler.package.scp.subprocess.run")
@patch("siliconcompiler.package.scp.shutil.which")
def test_command_with_custom_port(mock_which, mock_run, tmp_path):
    """Test that custom port is passed via -P flag in SCP command."""
    proj = Project("testproj")
    proj.option.set_cachedir(tmp_path)

    resolver = SCPResolver("testscp", proj, "scp://github.com:2222/test_owner/test_repo", "v1.0")
    mock_which.return_value = "/usr/bin/scp"
    mock_run.return_value = MagicMock(returncode=0)

    resolver.resolve_remote()

    args, _ = mock_run.call_args
    command = args[0]

    # Verify -P flag is present with correct port
    assert "-P" in command
    port_index = command.index("-P")
    assert command[port_index + 1] == "2222"
    # Host in the remote target should not contain the port
    remote_target = command[port_index + 2]
    assert remote_target == "github.com:/test_owner/test_repo"


# ============================================================================
# Integration Tests
# ============================================================================

@patch("siliconcompiler.package.scp.subprocess.run")
@patch("siliconcompiler.package.scp.shutil.which")
def test_get_resolver(mock_which, mock_run):
    """Test get_resolver returns correct mapping for SCP scheme."""
    from siliconcompiler.package.scp import get_resolver
    resolvers = get_resolver()
    assert isinstance(resolvers, dict)
    assert "scp" in resolvers
    assert resolvers["scp"] is SCPResolver


@patch("siliconcompiler.package.scp.subprocess.run")
@patch("siliconcompiler.package.scp.shutil.which")
def test_no_scp(mock_which, mock_run, tmp_path):
    """Test that proper error is raised when scp command not available."""
    proj = Project("testproj")
    proj.option.set_cachedir(tmp_path)

    resolver = SCPResolver("testscp", proj, "scp://github.com/test_owner/test_repo", "v1.0")
    mock_which.return_value = None

    with pytest.raises(RuntimeError, match=r"^SCP command not found\. "
                                           r"Please ensure SCP is installed and in your PATH\.$"):
        resolver.resolve()


@patch("siliconcompiler.package.scp.subprocess.run")
@patch("siliconcompiler.package.scp.shutil.which")
def test_download_scp(mock_which, mock_run, tmp_path):
    """Test successful download via SCP (legacy test)."""
    proj = Project("testproj")
    proj.option.set_cachedir(tmp_path)

    resolver = SCPResolver("testscp", proj, "scp://github.com/test_owner/test_repo", "v1.0")
    mock_run.return_value = MagicMock(returncode=0)
    mock_which.return_value = "/usr/bin/scp"

    result = resolver.resolve()

    assert isinstance(result, Path)
    assert "testscp-v1.0" in str(result)
    mock_which.assert_called_once()
    mock_run.assert_called_once()
