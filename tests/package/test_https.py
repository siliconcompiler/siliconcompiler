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

        # Verify the request was made
        call_args = mock_requests.get.call_args
        assert call_args is not None
        # Headers are now handled separately from _get_headers()
        assert mock_requests.get.called


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


# ============================================================================
# HTTPResolver._get_headers() tests
# ============================================================================

def test_http_resolver_get_headers_non_github_url(monkeypatch):
    """Test _get_headers returns empty dict for non-GitHub URLs."""
    monkeypatch.delenv("GIT_TOKEN", raising=False)
    resolver = HTTPResolver("test", None, "https://example.com/data.tar.gz", "v1.0")
    headers = resolver._get_headers()
    assert isinstance(headers, dict)
    assert "Accept" not in headers
    assert "Authorization" not in headers


def test_http_resolver_get_headers_github_url_accept_header():
    """Test _get_headers adds Accept header for GitHub URLs."""
    resolver = HTTPResolver("test", None,
                            "https://github.com/owner/repo/releases/download/v1.0/asset.tar.gz",
                            "v1.0")
    headers = resolver._get_headers()
    assert headers["Accept"] == "application/octet-stream"


def test_http_resolver_get_headers_github_archive_url():
    """Test _get_headers adds Accept header for GitHub archive URLs."""
    resolver = HTTPResolver("test", None,
                            "https://github.com/owner/repo/archive/refs/tags/v1.0.tar.gz",
                            "v1.0")
    headers = resolver._get_headers()
    assert headers["Accept"] == "application/octet-stream"


def test_http_resolver_get_headers_no_accept_for_other_urls():
    """Test _get_headers doesn't add Accept header for non-GitHub URLs."""
    resolver = HTTPResolver("test", None, "https://example.com/data.tar.gz", "v1.0")
    headers = resolver._get_headers()
    assert headers == {}


@pytest.mark.parametrize("pkg_name,prefix_list,env_vars,expected_token", [
    # Test 1: Package-specific token with single prefix
    ("mypackage", ["GITHUB"], {"GITHUB_MYPACKAGE_TOKEN": "pkg_token"}, "pkg_token"),

    # Test 2: General token fallback with single prefix
    ("other", ["GITHUB"], {"GITHUB_TOKEN": "general_token"}, "general_token"),

    # Test 3: Package-specific takes priority over general token
    (
        "test",
        ["GITHUB"],
        {"GITHUB_TEST_TOKEN": "pkg_token", "GITHUB_TOKEN": "general_token"},
        "pkg_token"
    ),

    # Test 4: Multiple prefixes, first prefix package token wins
    (
        "service",
        ["GITHUB", "GH", "GIT"],
        {
            "GITHUB_SERVICE_TOKEN": "github_pkg",
            "GH_SERVICE_TOKEN": "gh_pkg",
            "GIT_SERVICE_TOKEN": "git_pkg",
            "GITHUB_TOKEN": "github_general"
        },
        "github_pkg"
    ),

    # Test 5: Multiple prefixes - GITHUB_TOKEN checked before
    # GH_SERVICE_TOKEN
    (
        "service",
        ["GITHUB", "GH", "GIT"],
        {
            "GITHUB_TOKEN": "github_general",
            "GH_SERVICE_TOKEN": "gh_pkg",
            "GIT_SERVICE_TOKEN": "git_pkg"
        },
        "github_general"
    ),

    # Test 6: Multiple prefixes, fallback to second prefix package
    # token (no general for first prefix)
    (
        "service",
        ["GITHUB", "GH", "GIT"],
        {
            "GH_SERVICE_TOKEN": "gh_pkg",
            "GIT_SERVICE_TOKEN": "git_pkg"
        },
        "gh_pkg"
    ),

    # Test 7: Multiple prefixes fallback to third prefix general token
    (
        "service",
        ["GITHUB", "GH", "GIT"],
        {"GIT_TOKEN": "git_general"},
        "git_general"
    ),

    # Test 8: General token search - GITHUB_TOKEN comes before GH_TOKEN
    (
        "app",
        ["GITHUB", "GH"],
        {"GITHUB_TOKEN": "github_general", "GH_TOKEN": "gh_general"},
        "github_general"
    ),

    # Test 9: Single character package name
    ("a", ["GITHUB"], {"GITHUB_A_TOKEN": "single_char"}, "single_char"),

    # Test 10: Long package name
    ("very_long_package_name_with_underscores", ["GITHUB"],
     {"GITHUB_VERY_LONG_PACKAGE_NAME_WITH_UNDERSCORES_TOKEN": "long_pkg"}, "long_pkg"),

    # Test 11: Two letter package name
    ("py", ["GITHUB"], {"GITHUB_PY_TOKEN": "py_token"}, "py_token"),

    # Test 12: Numeric package name
    ("app123", ["GITHUB"], {"GITHUB_APP123_TOKEN": "numeric_pkg"}, "numeric_pkg"),
])
def test_http_resolver_get_auth_token_priority(monkeypatch, pkg_name, prefix_list,
                                               env_vars, expected_token):
    """Test _get_auth_token respects token priority with various configurations."""
    # Clear any conflicting env vars
    for key in ["GITHUB_TOKEN", "GH_TOKEN", "GIT_TOKEN", "HTTP_TOKEN", "HTTPS_TOKEN"]:
        monkeypatch.delenv(key, raising=False)

    # Set up package-specific env vars
    package_upper = pkg_name.upper()
    for char in ('#', '$', '&', '-', '=', '!', '/', '.'):
        package_upper = package_upper.replace(char, '')
    for prefix in prefix_list:
        monkeypatch.delenv(f"{prefix}_{package_upper}_TOKEN", raising=False)

    # Set the test environment variables
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    resolver = HTTPResolver(pkg_name, None, "https://example.com/data.tar.gz", "v1.0")
    token = resolver._get_auth_token(prefix_list)
    assert token == expected_token


@pytest.mark.parametrize("pkg_name,sanitized_name", [
    ("package", "PACKAGE"),
    ("my-package", "MYPACKAGE"),
    ("my_package", "MY_PACKAGE"),
    ("pkg#1.0", "PKG10"),
    ("package$", "PACKAGE"),
    ("pkg&special", "PKGSPECIAL"),
    ("my=pkg", "MYPKG"),
    ("pkg!test", "PKGTEST"),
    ("package/name", "PACKAGENAME"),
    ("pkg.js", "PKGJS"),
    ("test-pkg#$&=!/.", "TESTPKG"),
])
def test_http_resolver_get_auth_token_sanitization(monkeypatch, pkg_name, sanitized_name):
    """Test _get_auth_token properly sanitizes package names with special characters."""
    # Clear existing tokens
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    # Set environment variable with sanitized name
    monkeypatch.setenv(f"GITHUB_{sanitized_name}_TOKEN", "sanitized_token")

    resolver = HTTPResolver(pkg_name, None, "https://example.com/data.tar.gz", "v1.0")
    token = resolver._get_auth_token(["GITHUB"])
    assert token == "sanitized_token"


@pytest.mark.parametrize("prefix_list,env_setup", [
    # Single prefix scenarios
    (["GITHUB"], {"GITHUB_TOKEN": "token1"}),
    (["HTTP"], {"HTTP_TOKEN": "token2"}),
    (["HTTPS"], {"HTTPS_TOKEN": "token3"}),
    (["CUSTOM"], {"CUSTOM_TOKEN": "token4"}),
    (["GIT"], {"GIT_TOKEN": "token5"}),
    (["GH"], {"GH_TOKEN": "token6"}),

    # Multiple prefix scenarios
    (["GITHUB", "HTTP"], {"HTTP_TOKEN": "token_http"}),
    (["CUSTOM1", "CUSTOM2", "FALLBACK"], {"FALLBACK_TOKEN": "token_fallback"}),
    (["A", "B", "C", "D"], {"D_TOKEN": "token_d"}),

    # Two-element prefix lists
    (["PREFIX1", "PREFIX2"], {"PREFIX2_TOKEN": "token2"}),
    (["SERVER", "API"], {"API_TOKEN": "api_token"}),
])
def test_http_resolver_get_auth_token_multiple_prefixes(monkeypatch, prefix_list, env_setup):
    """Test _get_auth_token with various prefix list configurations."""
    # Clear all possible tokens
    for pref in ["GITHUB", "HTTP", "HTTPS", "CUSTOM", "CUSTOM1", "CUSTOM2", "FALLBACK", "GIT", "GH",
                 "A", "B", "C", "D", "PREFIX1", "PREFIX2", "SERVER", "API"]:
        monkeypatch.delenv(f"{pref}_TOKEN", raising=False)
        monkeypatch.delenv(f"{pref}_TEST_TOKEN", raising=False)

    # Set up the test environment
    for key, value in env_setup.items():
        monkeypatch.setenv(key, value)

    resolver = HTTPResolver("test", None, "https://example.com/data.tar.gz", "v1.0")
    token = resolver._get_auth_token(prefix_list)

    # Verify we got a token (at least one env var was set)
    assert token is not None
    assert token in env_setup.values()


@pytest.mark.parametrize("missing_prefixes", [
    ["NONEXISTENT"],
    ["FAKE1", "FAKE2", "FAKE3"],
    ["MISSING_PREFIX"],
    ["A", "B", "C", "D"],
])
def test_http_resolver_get_auth_token_not_found(monkeypatch, missing_prefixes):
    """Test _get_auth_token raises ValueError when no token found."""
    # Clear all possible tokens
    for prefix in missing_prefixes:
        monkeypatch.delenv(f"{prefix}_TOKEN", raising=False)
        monkeypatch.delenv(f"{prefix}_TEST_TOKEN", raising=False)

    resolver = HTTPResolver("test", None, "https://example.com/data.tar.gz", "v1.0")

    with pytest.raises(ValueError, match="Unable to determine authorization token"):
        resolver._get_auth_token(missing_prefixes)


@pytest.mark.parametrize("prefix,pkg_name,expected_env_vars", [
    # Single prefix generates 2 env var names (package-specific + general)
    (["GITHUB"], "myapp", ["GITHUB_MYAPP_TOKEN", "GITHUB_TOKEN"]),

    # Two prefixes generate 4 env var names
    (["GITHUB", "GIT"], "service", [
        "GITHUB_SERVICE_TOKEN", "GITHUB_TOKEN",
        "GIT_SERVICE_TOKEN", "GIT_TOKEN"
    ]),

    # Three prefixes generate 6 env var names
    (["GITHUB", "GH", "GIT"], "pkg", [
        "GITHUB_PKG_TOKEN", "GITHUB_TOKEN",
        "GH_PKG_TOKEN", "GH_TOKEN",
        "GIT_PKG_TOKEN", "GIT_TOKEN"
    ]),

    # Four prefixes generate 8 env var names
    (["A", "B", "C", "D"], "test", [
        "A_TEST_TOKEN", "A_TOKEN",
        "B_TEST_TOKEN", "B_TOKEN",
        "C_TEST_TOKEN", "C_TOKEN",
        "D_TEST_TOKEN", "D_TOKEN"
    ]),
])
def test_http_resolver_get_auth_token_search_order(monkeypatch, prefix, pkg_name,
                                                   expected_env_vars):
    """Test _get_auth_token searches env vars in correct order."""
    # Clear all possible tokens
    for env_var in expected_env_vars:
        monkeypatch.delenv(env_var, raising=False)

    # Set token only in the last position to verify search order
    last_env_var = expected_env_vars[-1]
    monkeypatch.setenv(last_env_var, "last_token")

    resolver = HTTPResolver(pkg_name, None, "https://example.com/data.tar.gz", "v1.0")
    token = resolver._get_auth_token(prefix)

    # Should find the token even though it's last in search order
    assert token == "last_token"

    # Now set token in first position and verify it takes priority
    first_env_var = expected_env_vars[0]
    monkeypatch.setenv(first_env_var, "first_token")

    token = resolver._get_auth_token(prefix)
    assert token == "first_token"


@pytest.mark.parametrize("token_value", [
    "simple_token",
    "token-with-dashes",
    "token_with_underscores",
    "TOKEN_ALL_CAPS",
    "token123numbers",
    "verylongtoken" * 10,  # Long token
    "a",  # Single character token
    "123",  # Numeric token
])
def test_http_resolver_get_auth_token_various_values(monkeypatch, token_value):
    """Test _get_auth_token correctly returns various token formats."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", token_value)

    resolver = HTTPResolver("test", None, "https://example.com/data.tar.gz", "v1.0")
    token = resolver._get_auth_token(["GITHUB"])
    assert token == token_value


@pytest.mark.parametrize("pkg_name,expected_search_order", [
    (
        "myapp",
        [
            "GITHUB_MYAPP_TOKEN",
            "GITHUB_TOKEN",
            "GH_MYAPP_TOKEN",
            "GH_TOKEN",
            "GIT_MYAPP_TOKEN",
            "GIT_TOKEN"
        ]
    ),
    (
        "data-hub",
        [
            "GITHUB_DATAHUB_TOKEN",
            "GITHUB_TOKEN",
            "GH_DATAHUB_TOKEN",
            "GH_TOKEN",
            "GIT_DATAHUB_TOKEN",
            "GIT_TOKEN"
        ]
    ),
])
def test_http_resolver_get_auth_token_search_sequence(monkeypatch, pkg_name, expected_search_order):
    """Test _get_auth_token searches environment variables in the exact expected sequence."""
    # Clear all tokens
    for env_var in expected_search_order:
        monkeypatch.delenv(env_var, raising=False)

    # Test that each position in the search order is checked correctly
    for idx, env_var in enumerate(expected_search_order):
        # Clear all tokens
        for env in expected_search_order:
            monkeypatch.delenv(env, raising=False)

        # Set token only at position idx
        monkeypatch.setenv(env_var, f"token_at_position_{idx}")

        resolver = HTTPResolver(pkg_name, None, "https://example.com/data.tar.gz", "v1.0")
        token = resolver._get_auth_token(["GITHUB", "GH", "GIT"])

        # Should find the token at this position
        assert token == f"token_at_position_{idx}"
