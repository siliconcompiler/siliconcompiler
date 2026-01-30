import logging
import pytest
import re
import responses
import tarfile
import zipfile
import os
import os.path

from io import BytesIO
from pathlib import Path
from unittest.mock import patch, MagicMock

from siliconcompiler.package.https import HTTPResolver
from siliconcompiler import Project


@pytest.mark.parametrize('path,ref,cache_id', [
    ('https://github.com/siliconcompiler/siliconcompiler/archive/',
     '938df309b4803fd79b10de6d3c7d7aa4645c39f5',
     '41c97ada2b142ac7'),
    ('https://github.com/siliconcompiler/siliconcompiler/archive/refs/heads/main.tar.gz',
     'version-1',
     '5440a5a4d2cd71bc')
])
@responses.activate
def test_dependency_path_download_http(datadir, path, ref, cache_id, tmp_path, monkeypatch, caplog):
    with open(os.path.join(datadir, 'https.tar.gz'), "rb") as f:
        responses.add(
            responses.GET,
            re.compile(r"https://github.com/siliconcompiler/siliconcompiler/.*\.tar.gz"),
            body=f.read(),
            status=200,
            content_type="application/x-gzip"
        )

    proj = Project("testproj")
    proj.set("option", "cachedir", tmp_path)
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    resolver = HTTPResolver("sc-data", proj, path, ref)
    assert resolver.resolve() == Path(os.path.join(tmp_path, f"sc-data-{ref[0:16]}-{cache_id}"))
    assert os.path.isfile(
        os.path.join(tmp_path, f"sc-data-{ref[0:16]}-{cache_id}", "pyproject.toml"))
    assert "Downloading sc-data data from " in caplog.text


@responses.activate
def test_dependency_path_download_http_failed():
    responses.add(
        responses.GET,
        re.compile(r".*"),
        status=400,
        content_type="application/x-gzip"
    )

    resolver = HTTPResolver(
        "sc-data",
        Project("testproj"),
        "https://github.com/siliconcompiler/siliconcompiler/archive/refs/heads/main.tar.gz",
        "main"
    )

    with pytest.raises(FileNotFoundError,
                       match=r"^Failed to download sc-data data source from "
                             r"https://.*\.tar\.gz\. Status code: 400$"):
        resolver.resolve()


# ============================================================================
# Additional HTTPResolver Tests
# ============================================================================

def test_http_resolver_get_resolver():
    """Test get_resolver returns correct mapping for HTTP/HTTPS schemes."""
    from siliconcompiler.package.https import get_resolver
    resolvers = get_resolver()
    assert isinstance(resolvers, dict)
    assert "http" in resolvers
    assert "https" in resolvers
    assert resolvers["http"] is HTTPResolver
    assert resolvers["https"] is HTTPResolver


def test_http_resolver_check_cache_not_exists():
    """Test check_cache returns False when cache path doesn't exist."""
    resolver = HTTPResolver("test", None, "https://example.com/data.tar.gz", "v1.0")
    with patch("os.path.exists", return_value=False):
        assert resolver.check_cache() is False


def test_http_resolver_check_cache_exists():
    """Test check_cache returns True when cache path exists."""
    resolver = HTTPResolver("test", None, "https://example.com/data.tar.gz", "v1.0")
    with patch("os.path.exists", return_value=True):
        assert resolver.check_cache() is True


def test_http_resolver_download_url_with_slash():
    """Test download_url construction when source ends with slash."""
    resolver = HTTPResolver("test", None, "https://example.com/data/", "v1.0")
    assert resolver.download_url == "https://example.com/data/v1.0.tar.gz"


def test_http_resolver_download_url_without_slash():
    """Test download_url construction when source doesn't end with slash."""
    resolver = HTTPResolver("test", None, "https://example.com/data.tar.gz", "v1.0")
    assert resolver.download_url == "https://example.com/data.tar.gz"


def test_http_resolver_download_url_complex():
    """Test download_url with complex URL."""
    resolver = HTTPResolver("test", None, "https://user:pass@example.com/path/", "ref")
    assert resolver.download_url == "https://user:pass@example.com/path/ref.tar.gz"


def test_http_resolver_resolve_remote_tarball(monkeypatch, tmpdir):
    """Test resolve_remote extracts tar.gz correctly."""
    project = Project("testproj")
    project.set("option", "cachedir", str(tmpdir))

    resolver = HTTPResolver("test", project, "https://example.com/data.tar.gz", "v1.0")

    # Create a test tar.gz in memory
    tar_buffer = BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode='w:gz') as tar:
        info = tarfile.TarInfo(name="test_file.txt")
        info.size = 5
        tar.addfile(info, BytesIO(b"hello"))
    tar_buffer.seek(0)

    import siliconcompiler.package.https as https_module
    with patch.object(https_module, "requests") as mock_requests:

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.content = tar_buffer.getvalue()
        mock_requests.get.return_value = mock_response

        resolver.resolve_remote()

        # Verify the file was extracted
        assert os.path.exists(os.path.join(str(resolver.cache_path), "test_file.txt"))


def test_http_resolver_resolve_remote_with_auth_token(monkeypatch, tmpdir):
    """Test resolve_remote uses GIT_TOKEN for authentication."""
    monkeypatch.setenv("GIT_TOKEN", "test_token_123")

    project = Project("testproj")
    project.set("option", "cachedir", str(tmpdir))

    resolver = HTTPResolver("test", project, "https://example.com/data.tar.gz", "v1.0")

    tar_buffer = BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode='w:gz'):
        pass
    tar_buffer.seek(0)

    import siliconcompiler.package.https as https_module
    with patch.object(https_module, "requests") as mock_requests:

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.content = tar_buffer.getvalue()
        mock_requests.get.return_value = mock_response

        resolver.resolve_remote()

        # Verify the token was passed in headers
        call_args = mock_requests.get.call_args
        headers = call_args[1]["headers"]
        assert "Authorization" in headers
        assert "test_token_123" in headers["Authorization"]


def test_http_resolver_resolve_remote_github_header(tmpdir):
    """Test resolve_remote sets GitHub-specific Accept header."""
    project = Project("testproj")
    project.set("option", "cachedir", str(tmpdir))

    resolver = HTTPResolver("test", project,
                            "https://github.com/owner/repo/releases/download/v1.0/file.tar.gz",
                            "v1.0")

    tar_buffer = BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode='w:gz'):
        pass
    tar_buffer.seek(0)

    import siliconcompiler.package.https as https_module
    with patch.object(https_module, "requests") as mock_requests:

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.content = tar_buffer.getvalue()
        mock_requests.get.return_value = mock_response

        resolver.resolve_remote()

        call_args = mock_requests.get.call_args
        headers = call_args[1]["headers"]
        assert headers.get("Accept") == "application/octet-stream"


def test_http_resolver_resolve_remote_download_failed():
    """Test resolve_remote raises error when download fails."""
    resolver = HTTPResolver("test", Project("testproj"),
                            "https://example.com/notfound.tar.gz", "v1.0")

    import siliconcompiler.package.https as https_module
    with patch.object(https_module, "requests") as mock_requests:
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 404
        mock_requests.get.return_value = mock_response

        with pytest.raises(FileNotFoundError, match="Failed to download"):
            resolver.resolve_remote()


def test_http_resolver_resolve_remote_invalid_archive(tmpdir):
    """Test resolve_remote raises error for invalid archive."""
    project = Project("testproj")
    project.set("option", "cachedir", str(tmpdir))

    resolver = HTTPResolver("test", project, "https://example.com/invalid.tar.gz", "v1.0")

    import siliconcompiler.package.https as https_module
    with patch.object(https_module, "requests") as mock_requests:

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.content = b"not a valid archive"
        mock_requests.get.return_value = mock_response

        with pytest.raises(TypeError, match="not a valid tar.gz or zip archive"):
            resolver.resolve_remote()


def test_http_resolver_resolve_remote_zip_file(tmpdir):
    """Test resolve_remote extracts zip files correctly."""
    project = Project("testproj")
    project.set("option", "cachedir", str(tmpdir))

    resolver = HTTPResolver("test", project, "https://example.com/data.zip", "v1.0")

    # Create a test zip in memory
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zf:
        zf.writestr("test_file.txt", "hello")
    zip_buffer.seek(0)

    import siliconcompiler.package.https as https_module
    with patch.object(https_module, "requests") as mock_requests:

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.content = zip_buffer.getvalue()
        mock_requests.get.return_value = mock_response

        resolver.resolve_remote()

        assert os.path.exists(os.path.join(str(resolver.cache_path), "test_file.txt"))


def test_http_resolver_resolve_remote_github_flatten(tmpdir):
    """Test resolve_remote flattens GitHub archive structure."""
    project = Project("testproj")
    project.set("option", "cachedir", str(tmpdir))

    resolver = HTTPResolver("test", project,
                            "https://github.com/owner/repo/archive/refs/tags/v1.0.tar.gz", "v1.0")

    tar_buffer = BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode='w:gz') as tar:
        info = tarfile.TarInfo(name="repo-1.0/test.txt")
        info.size = 4
        tar.addfile(info, BytesIO(b"test"))
    tar_buffer.seek(0)

    import siliconcompiler.package.https as https_module
    with patch.object(https_module, "requests") as mock_requests:

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.content = tar_buffer.getvalue()
        mock_requests.get.return_value = mock_response

        resolver.resolve_remote()

        # Verify file was moved to cache root
        assert os.path.exists(os.path.join(str(resolver.cache_path), "test.txt"))
        assert not os.path.exists(os.path.join(str(resolver.cache_path), "repo-1.0"))


def test_http_resolver_resolve_remote_bz2_tarball(tmpdir):
    """Test resolve_remote extracts bz2 tarballs."""
    project = Project("testproj")
    project.set("option", "cachedir", str(tmpdir))

    resolver = HTTPResolver("test", project, "https://example.com/data.tar.bz2", "v1.0")

    tar_buffer = BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode='w:bz2') as tar:
        info = tarfile.TarInfo(name="test.txt")
        info.size = 4
        tar.addfile(info, BytesIO(b"test"))
    tar_buffer.seek(0)

    import siliconcompiler.package.https as https_module
    with patch.object(https_module, "requests") as mock_requests:

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.content = tar_buffer.getvalue()
        mock_requests.get.return_value = mock_response

        resolver.resolve_remote()

        assert os.path.exists(os.path.join(str(resolver.cache_path), "test.txt"))


def test_http_resolver_resolve_remote_github_flatten_tgz(tmpdir):
    """Test resolve_remote flattens GitHub archive structure with .tgz extension."""
    project = Project("testproj")
    project.set("option", "cachedir", str(tmpdir))

    resolver = HTTPResolver("test", project,
                            "https://github.com/owner/repo/archive/refs/tags/v1.0.tgz", "v1.0")

    tar_buffer = BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode='w:gz') as tar:
        info = tarfile.TarInfo(name="repo-1.0/test.txt")
        info.size = 4
        tar.addfile(info, BytesIO(b"test"))
    tar_buffer.seek(0)

    import siliconcompiler.package.https as https_module
    with patch.object(https_module, "requests") as mock_requests:

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.content = tar_buffer.getvalue()
        mock_requests.get.return_value = mock_response

        resolver.resolve_remote()

        # Verify file was moved to cache root
        assert os.path.exists(os.path.join(str(resolver.cache_path), "test.txt"))
        assert not os.path.exists(os.path.join(str(resolver.cache_path), "repo-1.0"))
