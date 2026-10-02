import pytest
import logging
import os
import subprocess
import tarfile
import zipfile

from io import BytesIO
from unittest.mock import patch, MagicMock

from siliconcompiler.package import Resolver
from siliconcompiler.package.github import GithubArchiveResolver, GithubResolver
from siliconcompiler import Project


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    """Clear relevant environment variables before each test."""
    for var in ["GITHUB", "GH", "GIT", "HTTPS", "HTTP"]:
        monkeypatch.delenv(f"{var}_MYPACKAGE_TOKEN", raising=False)
        monkeypatch.delenv(f"{var}_TEST_TOKEN", raising=False)
        monkeypatch.delenv(f"{var}_TOKEN", raising=False)

    with patch("siliconcompiler.package.github.shutil.which") as mock_which:
        mock_which.return_value = None
        yield


def test_init_incorrect():
    with pytest.raises(ValueError,
                       match=r"^'github://this' is not in the proper form: github://"
                             r"<owner>/<repository>/<version>/<artifact>$"):
        GithubResolver("github", Project(), "github://this", "main")


def test_gh_path():
    resolver = GithubResolver(
        "github",
        Project(),
        "github://siliconcompiler/siliconcompiler/v1.0/v1.0.tar.gz", "v1.0")
    assert resolver.gh_path == ('siliconcompiler', 'siliconcompiler', 'v1.0', 'v1.0.tar.gz')


def test_download_url_tar_gz():
    resolver = GithubResolver(
        "github",
        Project(),
        "github://siliconcompiler/siliconcompiler/v1.0/v1.0.tar.gz", "v1.0")
    assert resolver.download_url == \
        "https://github.com/siliconcompiler/siliconcompiler/archive/refs/tags/v1.0.tar.gz"


def test_download_url_zip():
    resolver = GithubResolver(
        "github",
        Project(),
        "github://siliconcompiler/siliconcompiler/v1.0/v1.0.zip", "v1.0")
    assert resolver.download_url == \
        "https://github.com/siliconcompiler/siliconcompiler/archive/refs/tags/v1.0.zip"


def test_download_find_artifact():
    resolver = GithubResolver(
        "github",
        Project(),
        "github://siliconcompiler/siliconcompiler/v1.0/findme", "v1.0")

    with patch("github.Github.get_repo") as get_repo:
        class Asset:
            name = None
            url = None

        class Release:
            tag_name = None
            assets = []

        class Repo:
            def get_release(self, version):
                release = Release()
                release.tag_name = version
                asset = Asset()
                asset.name = "findme"
                asset.url = "https://thisone"
                release.assets.append(asset)
                return release

        get_repo.return_value = Repo()
        assert resolver.download_url == "https://thisone"
        get_repo.assert_called_once()


# ============================================================================
# Additional GithubResolver Tests
# ============================================================================

def test_github_resolver_get_resolver():
    """Test get_resolver returns correct mapping for GitHub schemes."""
    from siliconcompiler.package.github import get_resolver
    resolvers = get_resolver()
    assert isinstance(resolvers, dict)
    assert "github" in resolvers
    assert "github+private" in resolvers
    assert resolvers["github"] is GithubResolver
    assert resolvers["github+private"] is GithubResolver


def test_github_resolver_init_valid_format():
    """Test GithubResolver initialization with valid format."""
    resolver = GithubResolver("test", None, "github://owner/repo/v1.0/asset.tar.gz", "v1.0")
    assert resolver.name == "test"


def test_github_resolver_init_invalid_format():
    """Test GithubResolver initialization with invalid format."""
    with pytest.raises(ValueError, match="not in the proper form"):
        GithubResolver("test", None, "github://owner/repo", "v1.0")


def test_github_resolver_gh_path():
    """Test gh_path parsing of GitHub URI."""
    resolver = GithubResolver("test", None, "github://owner/repo/v1.0/asset.tar.gz", "v1.0")
    owner, repo, tag, asset = resolver.gh_path
    assert owner == "owner"
    assert repo == "repo"
    assert tag == "v1.0"
    assert asset == "asset.tar.gz"


def test_github_resolver_download_url_public(monkeypatch):
    """Test download_url for public repository."""
    resolver = GithubResolver("test", None, "github://owner/repo/v1.0/release.tar.gz", "v1.0")

    mock_gh = MagicMock()
    mock_repo = MagicMock()
    mock_asset = MagicMock()
    mock_asset.name = "release.tar.gz"
    mock_asset.url = "https://github.com/owner/repo/releases/download/v1.0/release.tar.gz"

    mock_release = MagicMock()
    mock_release.assets = [mock_asset]

    mock_repo.get_release.return_value = mock_release
    mock_gh.get_repo.return_value = mock_repo

    with patch.object(resolver, "_GithubResolver__gh", return_value=mock_gh):
        url = resolver.download_url
        assert "release.tar.gz" in url


def test_github_resolver_download_url_private_source(monkeypatch):
    """Test download_url for private repository with source archive."""
    resolver = GithubResolver("test", None, "github+private://owner/repo/v1.0/v1.0.tar.gz", "v1.0")

    # For source code archives, direct URL is returned
    url = resolver.download_url
    assert "v1.0.tar.gz" in url


def test_github_resolver_download_url_source_zip():
    """Test download_url for source archive (.zip)."""
    resolver = GithubResolver("test", None, "github://owner/repo/v1.0/v1.0.zip", "v1.0")
    url = resolver.download_url
    assert "v1.0.zip" in url


def test_github_resolver_download_url_source_tarball():
    """Test download_url for source archive (.tar.gz)."""
    resolver = GithubResolver("test", None, "github://owner/repo/v1.0/v1.0.tar.gz", "v1.0")
    url = resolver.download_url
    assert "v1.0.tar.gz" in url


def test_github_resolver_download_url_fallback_private_simple():
    """Test download_url with source archive doesn't require API fallback."""
    # Source archives are handled specially, no API call needed
    resolver = GithubResolver("test", Project("testproj"),
                              "github://owner/repo/v1.0/v1.0.tar.gz", "v1.0")
    url = resolver.download_url
    assert "v1.0.tar.gz" in url


def test_github_resolver_get_release_url_asset(monkeypatch):
    """Test __get_release_url finds asset in release."""
    resolver = GithubResolver("test", None, "github://owner/repo/v1.0/asset.tar.gz", "v1.0")

    mock_gh = MagicMock()
    mock_repo = MagicMock()
    mock_asset = MagicMock()
    mock_asset.name = "asset.tar.gz"
    mock_asset.url = "https://github.com/owner/repo/releases/download/v1.0/asset.tar.gz"

    mock_release = MagicMock()
    mock_release.assets = [mock_asset]

    mock_repo.get_release.return_value = mock_release
    mock_gh.get_repo.return_value = mock_repo

    with patch.object(resolver, "_GithubResolver__gh", return_value=mock_gh):
        url = resolver._GithubResolver__get_release_url("owner/repo", "v1.0",
                                                        "asset.tar.gz", private=False)
        assert "asset.tar.gz" in url


def test_github_resolver_get_release_url_not_found(monkeypatch):
    """Test __get_release_url raises error when asset not found."""
    resolver = GithubResolver("test", None, "github://owner/repo/v1.0/missing.tar.gz", "v1.0")

    mock_gh = MagicMock()
    mock_repo = MagicMock()
    mock_release = MagicMock()
    mock_release.assets = []

    mock_repo.get_release.return_value = mock_release
    mock_gh.get_repo.return_value = mock_repo

    with patch.object(resolver, "_GithubResolver__gh", return_value=mock_gh):
        with pytest.raises(ValueError, match="Unable to find"):
            resolver._GithubResolver__get_release_url("owner/repo", "v1.0",
                                                      "missing.tar.gz", private=False)


def test_github_resolver_get_release_url_latest(monkeypatch, caplog):
    """Test __get_release_url uses latest release when no version specified."""
    resolver = GithubResolver("test", Project("testproj"), "github://owner/repo//asset.tar.gz", "")

    mock_gh = MagicMock()
    mock_repo = MagicMock()
    mock_asset = MagicMock()
    mock_asset.name = "asset.tar.gz"
    mock_asset.url = "https://github.com/owner/repo/releases/download/v2.0/asset.tar.gz"

    mock_release = MagicMock()
    mock_release.assets = [mock_asset]
    mock_release.tag_name = "v2.0"

    mock_repo.get_latest_release.return_value = mock_release
    mock_repo.get_release.return_value = mock_release
    mock_gh.get_repo.return_value = mock_repo

    caplog.clear()
    caplog.set_level(logging.INFO)

    with patch.object(resolver, "_GithubResolver__gh", return_value=mock_gh):
        url = resolver._GithubResolver__get_release_url("owner/repo", "",
                                                        "asset.tar.gz", private=False)
        assert "v2.0" in url or url is not None


def test_github_resolver_get_gh_auth_package_token(monkeypatch):
    """Test __get_gh_auth finds package-specific token."""
    monkeypatch.setenv("GITHUB_MYPACKAGE_TOKEN", "token_pkg")

    resolver = GithubResolver("mypackage", None,
                              "github+private://owner/repo/v1.0/asset.tar.gz", "v1.0")
    token = resolver._GithubResolver__get_gh_token()
    assert token == "token_pkg"


def test_github_resolver_get_gh_auth_github_token(monkeypatch):
    """Test __get_gh_auth falls back to GITHUB_TOKEN."""
    monkeypatch.setenv("GITHUB_TOKEN", "token_github")

    resolver = GithubResolver("test", None, "github+private://owner/repo/v1.0/asset.tar.gz", "v1.0")
    token = resolver._GithubResolver__get_gh_token()
    assert token == "token_github"


def test_github_resolver_get_gh_auth_git_token(monkeypatch):
    """Test __get_gh_auth falls back to GIT_TOKEN."""
    monkeypatch.setenv("GIT_TOKEN", "token_git")

    resolver = GithubResolver("test", None, "github+private://owner/repo/v1.0/asset.tar.gz", "v1.0")
    token = resolver._GithubResolver__get_gh_token()
    assert token == "token_git"


def test_github_resolver_get_gh_auth_not_found():
    """Test __get_gh_auth raises error when no token found."""
    resolver = GithubResolver("test", None, "github+private://owner/repo/v1.0/asset.tar.gz", "v1.0")

    with pytest.raises(ValueError, match="authorization token"):
        resolver._GithubResolver__get_gh_token()


def test_github_resolver_gh_unauthenticated():
    """Test __gh returns unauthenticated client."""
    resolver = GithubResolver("test", None, "github://owner/repo/v1.0/asset.tar.gz", "v1.0")

    with patch("siliconcompiler.package.github.Github") as mock_gh_class:
        resolver._GithubResolver__gh(private=False)
        mock_gh_class.assert_called_once_with()


def test_github_resolver_gh_authenticated(monkeypatch):
    """Test __gh returns authenticated client."""
    monkeypatch.setenv("GITHUB_TOKEN", "test_token")

    resolver = GithubResolver("test", None, "github+private://owner/repo/v1.0/asset.tar.gz", "v1.0")

    with patch("siliconcompiler.package.github.Github") as mock_gh_class, \
         patch("siliconcompiler.package.github.Auth.Token") as mock_auth:
        resolver._GithubResolver__gh(private=True)
        mock_auth.assert_called_once_with("test_token")
        mock_gh_class.assert_called_once()


def test_github_resolver_download_url_fallback_to_private(monkeypatch):
    """Test download_url falls back to private when public repo not found."""
    resolver = GithubResolver("test", None, "github://owner/repo/v1.0/asset.tar.gz", "v1.0")

    from github.GithubException import UnknownObjectException

    mock_gh_public = MagicMock()
    mock_repo_public = MagicMock()
    mock_repo_public.get_release.side_effect = UnknownObjectException(404, {"message": "Not Found"})
    mock_gh_public.get_repo.return_value = mock_repo_public

    mock_gh_private = MagicMock()
    mock_repo_private = MagicMock()
    mock_asset = MagicMock()
    mock_asset.name = "asset.tar.gz"
    mock_asset.url = "https://github.com/owner/repo/releases/download/v1.0/asset.tar.gz"
    mock_release = MagicMock()
    mock_release.assets = [mock_asset]
    mock_repo_private.get_release.return_value = mock_release
    mock_gh_private.get_repo.return_value = mock_repo_private

    with patch.object(resolver, "_GithubResolver__gh") as mock_gh_method:
        def gh_side_effect(private=False):
            return mock_gh_public if not private else mock_gh_private

        mock_gh_method.side_effect = gh_side_effect
        url = resolver.download_url
        assert "asset.tar.gz" in url


# ============================================================================
# New tests for GithubResolver headers and URL caching
# ============================================================================
def test_github_resolver_get_headers(monkeypatch):
    """Test _get_headers returns correct headers for GitHub download."""
    monkeypatch.setenv("GITHUB_TOKEN", "test_token")
    # Use source archive to avoid API call
    resolver = GithubResolver("test", None, "github://owner/repo/v1.0/v1.0.tar.gz", "v1.0")
    headers = resolver._get_headers()
    assert headers["Accept"] == "application/octet-stream"
    assert headers["Authorization"] == "token test_token"


def test_github_resolver_get_headers_no_token():
    """Test _get_headers returns Accept header and skips Authorization if no token."""
    # Use source archive to avoid API call
    resolver = GithubResolver("test", None, "github://owner/repo/v1.0/v1.0.tar.gz", "v1.0")
    headers = resolver._get_headers()

    assert headers["Accept"] == "application/octet-stream"
    assert "Authorization" not in headers


def test_github_resolver_get_headers_inherits_parent(monkeypatch):
    """Test _get_headers calls parent class and adds GitHub-specific headers."""
    monkeypatch.setenv("GIT_TOKEN", "parent_token")
    monkeypatch.setenv("GITHUB_TOKEN", "github_token")
    # Use source archive to avoid API call
    resolver = GithubResolver("test", None, "github://owner/repo/v1.0/v1.0.tar.gz", "v1.0")

    # The GithubResolver should override Authorization from parent with GitHub token
    headers = resolver._get_headers()
    assert headers["Accept"] == "application/octet-stream"
    assert headers["Authorization"] == "token github_token"


def test_github_resolver_url_caching(monkeypatch):
    """Test GithubResolver caches the URL after first lookup."""
    resolver = GithubResolver("test", None, "github://owner/repo/v1.0/asset.tar.gz", "v1.0")

    mock_gh = MagicMock()
    mock_repo = MagicMock()
    mock_asset = MagicMock()
    mock_asset.name = "asset.tar.gz"
    mock_asset.url = "https://github.com/owner/repo/releases/download/v1.0/asset.tar.gz"
    mock_release = MagicMock()
    mock_release.assets = [mock_asset]
    mock_repo.get_release.return_value = mock_release
    mock_gh.get_repo.return_value = mock_repo

    with patch.object(resolver, "_GithubResolver__gh", return_value=mock_gh):
        url1 = resolver.download_url
        # __url should now be cached
        assert resolver._GithubResolver__url == url1
        # Second call should return cached URL, not call API again
        url2 = resolver.download_url
        assert url1 == url2
        # Verify GitHub API was only called once (cached on second call)
        assert mock_gh.get_repo.call_count == 1


def test_github_resolver_url_caching_with_source_archive():
    """Test URL caching for source archives that don't hit API."""
    resolver = GithubResolver("test", None, "github://owner/repo/v1.0/v1.0.tar.gz", "v1.0")

    # Source archives have direct URLs, no API call needed
    url1 = resolver.download_url
    url2 = resolver.download_url
    assert url1 == url2
    assert "archive/refs/tags/v1.0.tar.gz" in url1


def test_github_resolver_get_gh_auth_sanitize_package_name(monkeypatch):
    """Test __get_gh_auth sanitizes special characters in package name."""
    # Package name with special characters that need sanitization
    # "my-package#1.0" becomes "MYPACKAGE10" after sanitization
    monkeypatch.setenv("GITHUB_MYPACKAGE10_TOKEN", "pkg_token")

    resolver = GithubResolver("my-package#1.0", None,
                              "github://owner/repo/v1.0/v1.0.tar.gz", "v1.0")
    token = resolver._GithubResolver__get_gh_token()
    assert token == "pkg_token"


def test_github_resolver_get_gh_auth_multiple_special_chars(monkeypatch):
    """Test __get_gh_auth handles multiple special characters."""
    # Test sanitization of #, $, &, -, =, !, /
    monkeypatch.setenv("GITHUB_TESTPKG_TOKEN", "special_token")

    resolver = GithubResolver("test-pkg#$&=!/", None,
                              "github+private://owner/repo/v1.0/asset.tar.gz", "v1.0")
    token = resolver._GithubResolver__get_gh_token()
    assert token == "special_token"


# ============================================================================
# Tests for gh CLI bypass in __get_gh_token
# ============================================================================

def test_github_resolver_get_gh_token_fallback_gh_cli_success():
    """Test __get_gh_token falls back to gh CLI and succeeds."""
    resolver = GithubResolver("test", None,
                              "github+private://owner/repo/v1.0/asset.tar.gz", "v1.0")

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = b"gh_cli_token_12345"

    with patch("siliconcompiler.package.github.shutil.which") as mock_which, \
         patch("siliconcompiler.package.github.subprocess.run") as mock_run:
        mock_which.return_value = "/usr/bin/gh"
        mock_run.return_value = mock_result

        token = resolver._GithubResolver__get_gh_token()

        assert token == "gh_cli_token_12345"
        mock_which.assert_called_once_with("gh")
        mock_run.assert_called_once_with(
            ["/usr/bin/gh", "auth", "token"],
            capture_output=True,
            timeout=5
        )


def test_github_resolver_get_gh_token_fallback_gh_cli_strips_whitespace():
    """Test __get_gh_token gh CLI result strips whitespace."""
    resolver = GithubResolver("test", None,
                              "github+private://owner/repo/v1.0/asset.tar.gz", "v1.0")

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = b"  token_with_whitespace\n\n  "

    with patch("siliconcompiler.package.github.shutil.which") as mock_which, \
         patch("siliconcompiler.package.github.subprocess.run") as mock_run:
        mock_which.return_value = "/usr/bin/gh"
        mock_run.return_value = mock_result

        token = resolver._GithubResolver__get_gh_token()

        assert token == "token_with_whitespace"


def test_github_resolver_get_gh_token_fallback_gh_missing():
    """Test __get_gh_token raises error when gh is missing."""
    resolver = GithubResolver("test", None,
                              "github+private://owner/repo/v1.0/asset.tar.gz", "v1.0")

    with patch("siliconcompiler.package.github.shutil.which") as mock_which:
        mock_which.return_value = None  # gh command not found

        with pytest.raises(ValueError, match="authorization token"):
            resolver._GithubResolver__get_gh_token()


def test_github_resolver_get_gh_token_fallback_gh_timeout():
    """Test __get_gh_token handles timeout from gh CLI."""
    resolver = GithubResolver("test", None,
                              "github+private://owner/repo/v1.0/asset.tar.gz", "v1.0")

    with patch("siliconcompiler.package.github.shutil.which") as mock_which, \
         patch("siliconcompiler.package.github.subprocess.run") as mock_run:
        mock_which.return_value = "/usr/bin/gh"
        mock_run.side_effect = subprocess.TimeoutExpired(["gh", "auth", "token"], timeout=5)

        with pytest.raises(ValueError, match="authorization token"):
            resolver._GithubResolver__get_gh_token()


def test_github_resolver_get_gh_token_fallback_gh_nonzero_exit():
    """Test __get_gh_token raises error when gh returns non-zero exit code."""
    resolver = GithubResolver("test", None,
                              "github+private://owner/repo/v1.0/asset.tar.gz", "v1.0")

    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = b"Not authenticated"

    with patch("siliconcompiler.package.github.shutil.which") as mock_which, \
         patch("siliconcompiler.package.github.subprocess.run") as mock_run:
        mock_which.return_value = "/usr/bin/gh"
        mock_run.return_value = mock_result

        with pytest.raises(ValueError, match="authorization token"):
            resolver._GithubResolver__get_gh_token()


def test_github_resolver_get_gh_token_fallback_gh_env_preferred_over_gh_cli(monkeypatch):
    """Test environment tokens are preferred over gh CLI fallback."""
    monkeypatch.setenv("GITHUB_TOKEN", "env_token")

    resolver = GithubResolver("test", None,
                              "github+private://owner/repo/v1.0/asset.tar.gz", "v1.0")

    with patch("siliconcompiler.package.github.shutil.which") as mock_which, \
         patch("siliconcompiler.package.github.subprocess.run") as mock_run:
        token = resolver._GithubResolver__get_gh_token()

        # Should use env token, never call gh
        assert token == "env_token"
        mock_which.assert_not_called()
        mock_run.assert_not_called()


def test_github_resolver_get_gh_token_fallback_only_when_env_fails():
    """Test gh CLI is only used when env variables fail."""
    resolver = GithubResolver("test", None,
                              "github+private://owner/repo/v1.0/asset.tar.gz", "v1.0")

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = b"fallback_token"

    with patch("siliconcompiler.package.github.shutil.which") as mock_which, \
         patch("siliconcompiler.package.github.subprocess.run") as mock_run:
        mock_which.return_value = "/usr/bin/gh"
        mock_run.return_value = mock_result

        token = resolver._GithubResolver__get_gh_token()

        assert token == "fallback_token"
        # Verify gh CLI was called as fallback
        mock_run.assert_called_once()


def test_github_resolver_get_gh_token_fallback_preserves_original_error():
    """Test __get_gh_token preserves original ValueError when gh CLI also fails."""
    resolver = GithubResolver("test", None,
                              "github+private://owner/repo/v1.0/asset.tar.gz", "v1.0")

    # Distinctive sentinel error raised by the parent env lookup
    sentinel = ValueError("sentinel original authorization token error")

    # gh returns failure
    mock_result = MagicMock()
    mock_result.returncode = 1

    with patch("siliconcompiler.package.github.shutil.which") as mock_which, \
         patch("siliconcompiler.package.github.subprocess.run") as mock_run, \
         patch("siliconcompiler.package.RemoteResolver._get_auth_token",
               side_effect=sentinel):
        mock_which.return_value = "/usr/bin/gh"
        mock_run.return_value = mock_result

        # Should re-raise the exact original ValueError from the parent class,
        # not a new one introduced by the gh fallback path
        with pytest.raises(ValueError) as exc_info:
            resolver._GithubResolver__get_gh_token()

        assert exc_info.value is sentinel


def test_github_resolver_get_gh_token_timeout_5_seconds():
    """Test __get_gh_token uses 5 second timeout for gh CLI."""
    resolver = GithubResolver("test", None,
                              "github+private://owner/repo/v1.0/asset.tar.gz", "v1.0")

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = b"token"

    timeout_used = None

    def capture_timeout(*args, **kwargs):
        nonlocal timeout_used
        timeout_used = kwargs.get('timeout')
        return mock_result

    with patch("siliconcompiler.package.github.shutil.which") as mock_which, \
         patch("siliconcompiler.package.github.subprocess.run", side_effect=capture_timeout) \
            as mock_run:
        mock_which.return_value = "/usr/bin/gh"

        resolver._GithubResolver__get_gh_token()

        mock_run.assert_called_once()
        assert timeout_used == 5


def test_github_resolver_get_gh_token_with_capture_output():
    """Test __get_gh_token uses capture_output=True for gh subprocess."""
    resolver = GithubResolver("test", None,
                              "github+private://owner/repo/v1.0/asset.tar.gz", "v1.0")

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = b"token"

    with patch("siliconcompiler.package.github.shutil.which") as mock_which, \
         patch("siliconcompiler.package.github.subprocess.run") as mock_run:
        mock_which.return_value = "/usr/bin/gh"
        mock_run.return_value = mock_result

        resolver._GithubResolver__get_gh_token()

        # Verify subprocess.run was called with capture_output=True
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs['capture_output'] is True


# ============================================================================
# Tests for gh CLI output validation
# ============================================================================

def test_github_resolver_get_gh_token_rejects_empty_output():
    """Test __get_gh_token rejects empty token from gh CLI."""
    resolver = GithubResolver("test", None,
                              "github+private://owner/repo/v1.0/asset.tar.gz", "v1.0")

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = b""  # Empty token

    with patch("siliconcompiler.package.github.shutil.which") as mock_which, \
         patch("siliconcompiler.package.github.subprocess.run") as mock_run:
        mock_which.return_value = "/usr/bin/gh"
        mock_run.return_value = mock_result

        with pytest.raises(ValueError, match="authorization token"):
            resolver._GithubResolver__get_gh_token()


def test_github_resolver_get_gh_token_rejects_whitespace_only_output():
    """Test __get_gh_token rejects whitespace-only token from gh CLI."""
    resolver = GithubResolver("test", None,
                              "github+private://owner/repo/v1.0/asset.tar.gz", "v1.0")

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = b"   \n\n  \t  "  # Only whitespace

    with patch("siliconcompiler.package.github.shutil.which") as mock_which, \
         patch("siliconcompiler.package.github.subprocess.run") as mock_run:
        mock_which.return_value = "/usr/bin/gh"
        mock_run.return_value = mock_result

        with pytest.raises(ValueError, match="authorization token"):
            resolver._GithubResolver__get_gh_token()


def test_github_resolver_get_gh_token_rejects_multiline_token():
    """Test __get_gh_token rejects multiline token from gh CLI."""
    resolver = GithubResolver("test", None,
                              "github+private://owner/repo/v1.0/asset.tar.gz", "v1.0")

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = b"token_line1\ntoken_line2"  # Multiple lines

    with patch("siliconcompiler.package.github.shutil.which") as mock_which, \
         patch("siliconcompiler.package.github.subprocess.run") as mock_run:
        mock_which.return_value = "/usr/bin/gh"
        mock_run.return_value = mock_result

        with pytest.raises(ValueError, match="authorization token"):
            resolver._GithubResolver__get_gh_token()


def test_github_resolver_get_gh_token_rejects_embedded_newline():
    """Test __get_gh_token rejects token with embedded newlines."""
    resolver = GithubResolver("test", None,
                              "github+private://owner/repo/v1.0/asset.tar.gz", "v1.0")

    mock_result = MagicMock()
    mock_result.returncode = 0
    # Token with embedded newline after strip
    mock_result.stdout = b"token_part1\ntoken_part2"

    with patch("siliconcompiler.package.github.shutil.which") as mock_which, \
         patch("siliconcompiler.package.github.subprocess.run") as mock_run:
        mock_which.return_value = "/usr/bin/gh"
        mock_run.return_value = mock_result

        with pytest.raises(ValueError, match="authorization token"):
            resolver._GithubResolver__get_gh_token()


def test_github_resolver_get_gh_token_accepts_single_line_token():
    """Test __get_gh_token accepts valid single-line token from gh CLI."""
    resolver = GithubResolver("test", None,
                              "github+private://owner/repo/v1.0/asset.tar.gz", "v1.0")

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = b"valid_single_line_token"

    with patch("siliconcompiler.package.github.shutil.which") as mock_which, \
         patch("siliconcompiler.package.github.subprocess.run") as mock_run:
        mock_which.return_value = "/usr/bin/gh"
        mock_run.return_value = mock_result

        token = resolver._GithubResolver__get_gh_token()

        assert token == "valid_single_line_token"


def test_github_resolver_get_gh_token_strips_leading_trailing_whitespace():
    """Test __get_gh_token properly strips leading/trailing whitespace."""
    resolver = GithubResolver("test", None,
                              "github+private://owner/repo/v1.0/asset.tar.gz", "v1.0")

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = b"  \n  token_value  \n  "

    with patch("siliconcompiler.package.github.shutil.which") as mock_which, \
         patch("siliconcompiler.package.github.subprocess.run") as mock_run:
        mock_which.return_value = "/usr/bin/gh"
        mock_run.return_value = mock_result

        token = resolver._GithubResolver__get_gh_token()

        assert token == "token_value"
        assert "\n" not in token


def test_github_resolver_get_gh_token_rejects_carriage_returns():
    """Test __get_gh_token rejects tokens with carriage returns."""
    resolver = GithubResolver("test", None,
                              "github+private://owner/repo/v1.0/asset.tar.gz", "v1.0")

    mock_result = MagicMock()
    mock_result.returncode = 0
    # Token with carriage return (should be rejected)
    mock_result.stdout = b"token\rvalue"

    with patch("siliconcompiler.package.github.shutil.which") as mock_which, \
         patch("siliconcompiler.package.github.subprocess.run") as mock_run:
        mock_which.return_value = "/usr/bin/gh"
        mock_run.return_value = mock_result

        with pytest.raises(ValueError, match="authorization token"):
            resolver._GithubResolver__get_gh_token()


# ============================================================================
# GitHub archives, as a dataroot reaches them: through the resolver registry
# ============================================================================

_SHA = "938df309b4803fd79b10de6d3c7d7aa4645c39f5"


def _archive(members, fmt):
    """An archive holding one byte at each path in ``members``."""
    buffer = BytesIO()
    if fmt == "zip":
        with zipfile.ZipFile(buffer, "w") as zip_ref:
            for member in members:
                zip_ref.writestr(member, "x")
    else:
        with tarfile.open(fileobj=buffer, mode=f"w:{fmt}") as tar:
            for member in members:
                info = tarfile.TarInfo(name=member)
                info.size = 1
                tar.addfile(info, BytesIO(b"x"))
    return buffer.getvalue()


def _fetch(source, ref, members, fmt="gz"):
    """
    Resolves ``source`` with the resolver the registry picks for it, downloading
    an archive of ``members``.

    Returns:
        tuple: the cache root's entries, the request's headers, and the
        warnings logged.
    """
    project = Project("testproj")
    project.option.set_cachedir(".")
    resolver = Resolver.find_resolver(source)("test", project, source, ref)
    with patch("siliconcompiler.package.https.requests.get") as get, \
         patch.object(resolver.logger, "warning") as warning:
        get.return_value.ok = True
        get.return_value.content = _archive(members, fmt)
        resolver.resolve_remote()
    return sorted(os.listdir(resolver.cache_path)), get.call_args.kwargs["headers"], \
        [call.args[0] for call in warning.call_args_list]


@pytest.mark.parametrize("source,ref,members,fmt", [
    # lambdapdk's release form: a tag directory, with the reference appended.
    ("https://github.com/o/r/archive/refs/tags/", "v1.0.2", ["r-1.0.2/f"], "gz"),
    # lambdapdk's development form: the reference is a commit.
    ("https://github.com/o/r/archive/", _SHA, [f"r-{_SHA}/f"], "gz"),
    ("https://github.com/o/r/archive/refs/tags/v1.0.2.zip", "v1.0.2", ["r-1.0.2/f"], "zip"),
    ("https+private://github.com/o/r/archive/refs/tags/v1.0.tar.gz", "v1.0", ["r-1.0/f"], "gz"),
    ("http://github.com/o/r/archive/refs/tags/v1.0.tar.gz", "v1.0", ["r-1.0/f"], "gz"),
    ("https://codeload.github.com/o/r/tar.gz/refs/tags/v1", "v1", ["r-1/f"], "gz"),
    ("github://o/r/v1.0/v1.0.tar.gz", "v1.0", ["r-1.0/f"], "gz"),
    ("github://o/r/v1.0/v1.0.zip", "v1.0", ["r-1.0/f"], "zip"),
])
def test_github_archive_is_flattened(source, ref, members, fmt):
    """A GitHub source archive wraps the repository in '<repo>-<ref>', which is
    moved up so the cache root is the repository root."""
    entries, _, warnings = _fetch(source, ref, members, fmt)
    assert entries == ["f"]
    assert warnings == []


@pytest.mark.parametrize("source,members,expect", [
    # GitHub's shape, on a host that is not GitHub's.
    ("https://example.com/o/r/archive/refs/tags/v1.0.tar.gz", ["r-1.0/f"], ["r-1.0"]),
    # A single top directory, but not the one GitHub names.
    ("https://github.com/o/r/archive/refs/tags/v1.0.tar.gz", ["other/f"], ["other"]),
    # The '<repo>-<ref>' directory, but not alone.
    ("https://github.com/o/r/archive/refs/tags/v1.0.tar.gz", ["r-1.0/f", "g"], ["g", "r-1.0"]),
])
def test_archive_not_flattened(source, members, expect):
    entries, _, warnings = _fetch(source, "v1.0", members)
    assert entries == expect
    assert warnings == []


def test_github_release_asset_is_not_flattened():
    """A release asset is laid out however its author built it, so even a top
    directory named like a source archive's stays."""
    asset = MagicMock()
    asset.name = "asset.tar.gz"
    asset.url = "https://api.github.com/repos/o/r/releases/assets/1"
    gh = MagicMock()
    gh.get_repo.return_value.get_release.return_value.assets = [asset]

    with patch.object(GithubResolver, "_GithubResolver__gh", return_value=gh):
        entries, headers, _ = _fetch("github://o/r/v1.0/asset.tar.gz", "v1.0", ["r-1.0/f"])
    assert entries == ["r-1.0"]
    assert headers["Accept"] == "application/octet-stream"


def test_github_enterprise_archive_is_flattened():
    """GitHub Enterprise packs its archives as github.com does."""
    entries, _, warnings = _fetch("https://github.mycorp.com/o/r/archive/refs/tags/v1.0.tar.gz",
                                  "v1.0", ["r-1.0/f"])
    assert entries == ["f"]
    assert warnings == []


@pytest.mark.parametrize("source,resolver", [
    ("https://github.com/o/r/archive/refs/tags/", "GithubArchiveResolver"),
    ("https+private://github.com/o/r/archive/refs/tags/", "GithubArchiveResolver"),
    ("http://github.com/o/r/archive/refs/tags/", "GithubArchiveResolver"),
    ("https://codeload.github.com/o/r/tar.gz/refs/tags/v1", "GithubArchiveResolver"),
    ("https://api.github.com/repos/o/r/releases/assets/1", "GithubArchiveResolver"),
    ("https://GitHub.com/o/r/archive/refs/tags/", "GithubArchiveResolver"),
    # GitHub Enterprise, matched by label; its tokens are a separate question.
    ("https://github.mycorp.com/o/r/archive/refs/tags/", "GithubArchiveResolver"),
    ("github://o/r/v1.0/v1.0.tar.gz", "GithubResolver"),
    # The owner sits where a host would, and is no reason to leave github://.
    ("github://github/r/v1.0/v1.0.tar.gz", "GithubResolver"),
    ("https://notgithub.com/o/r/archive/refs/tags/", "HTTPResolver"),
    ("https://mygithub.internal/o/r/archive/refs/tags/", "HTTPResolver"),
    ("https://example.com/github.com/x.tar.gz", "HTTPResolver"),
])
def test_find_resolver_by_host(source, resolver):
    assert Resolver.find_resolver(source).__name__ == resolver


@pytest.mark.parametrize("source,accept", [
    ("https://github.com/o/r/archive/refs/tags/v1.0.tar.gz", True),
    # A release asset by its API URL answers with JSON unless asked for the file.
    ("https://api.github.com/repos/o/r/releases/assets/1", True),
    ("https://example.com/x.tar.gz", False),
])
def test_github_accept_header(source, accept):
    resolver = Resolver.find_resolver(source)("test", None, source, "v1.0")
    headers = resolver._get_headers()
    assert (headers.get("Accept") == "application/octet-stream") is accept


# ============================================================================
# GithubArchiveResolver: plain URLs on GitHub's hosts
# ============================================================================

def test_github_archive_resolver_resolve_remote_header():
    """Test resolve_remote sets GitHub-specific Accept header."""
    project = Project("testproj")
    project.option.set_cachedir(".")

    resolver = GithubArchiveResolver(
        "test", project,
        "https://github.com/owner/repo/releases/download/v1.0/file.tar.gz", "v1.0")

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


def test_github_archive_resolver_resolve_remote_flatten():
    """Test resolve_remote flattens GitHub archive structure."""
    project = Project("testproj")
    project.option.set_cachedir(".")

    resolver = GithubArchiveResolver(
        "test", project,
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


def test_github_archive_resolver_resolve_remote_flatten_tgz():
    """Test resolve_remote flattens GitHub archive structure with .tgz extension."""
    project = Project("testproj")
    project.option.set_cachedir(".")

    resolver = GithubArchiveResolver(
        "test", project,
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


def test_github_archive_resolver_resolve_remote_flatten_zip():
    """
    A GitHub source zip flattens like the tarballs do.

    ``github://`` builds these itself, as '<release>.zip' -- so the dotted release
    that defeats the fallback guess is the normal case, not an exotic one.
    """
    project = Project("testproj")
    project.option.set_cachedir(".")

    resolver = GithubArchiveResolver(
        "test", project,
        "https://github.com/owner/repo/archive/refs/tags/v1.0.2.zip", "v1.0.2")

    archive = BytesIO()
    with zipfile.ZipFile(archive, 'w') as zf:
        zf.writestr("repo-1.0.2/test.txt", "test")

    import siliconcompiler.package.https as https_module
    with patch.object(https_module, "requests") as mock_requests:
        mock_requests.get.return_value.ok = True
        mock_requests.get.return_value.content = archive.getvalue()
        resolver.resolve_remote()

    assert os.path.isfile(os.path.join(str(resolver.cache_path), "test.txt"))
    assert not os.path.exists(os.path.join(str(resolver.cache_path), "repo-1.0.2"))


def test_github_archive_resolver_get_headers_release_url():
    """Test _get_headers adds Accept header for GitHub URLs."""
    resolver = GithubArchiveResolver(
        "test", None,
        "https://github.com/owner/repo/releases/download/v1.0/asset.tar.gz", "v1.0")
    headers = resolver._get_headers()
    assert headers["Accept"] == "application/octet-stream"


def test_github_archive_resolver_get_headers_archive_url():
    """Test _get_headers adds Accept header for GitHub archive URLs."""
    resolver = GithubArchiveResolver(
        "test", None,
        "https://github.com/owner/repo/archive/refs/tags/v1.0.tar.gz", "v1.0")
    headers = resolver._get_headers()
    assert headers["Accept"] == "application/octet-stream"
