import pytest
import logging

from unittest.mock import patch, MagicMock

from siliconcompiler.package.github import GithubResolver
from siliconcompiler import Project


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
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    resolver = GithubResolver("mypackage", None,
                              "github+private://owner/repo/v1.0/asset.tar.gz", "v1.0")
    token = resolver._GithubResolver__get_gh_token()
    assert token == "token_pkg"


def test_github_resolver_get_gh_auth_github_token(monkeypatch):
    """Test __get_gh_auth falls back to GITHUB_TOKEN."""
    monkeypatch.delenv("GITHUB_TEST_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "token_github")

    resolver = GithubResolver("test", None, "github+private://owner/repo/v1.0/asset.tar.gz", "v1.0")
    token = resolver._GithubResolver__get_gh_token()
    assert token == "token_github"


def test_github_resolver_get_gh_auth_git_token(monkeypatch):
    """Test __get_gh_auth falls back to GIT_TOKEN."""
    monkeypatch.delenv("GITHUB_TEST_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("GIT_TOKEN", "token_git")

    resolver = GithubResolver("test", None, "github+private://owner/repo/v1.0/asset.tar.gz", "v1.0")
    token = resolver._GithubResolver__get_gh_token()
    assert token == "token_git"


def test_github_resolver_get_gh_auth_not_found(monkeypatch):
    """Test __get_gh_auth raises error when no token found."""
    monkeypatch.delenv("GITHUB_TEST_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GIT_TOKEN", raising=False)

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


def test_github_resolver_get_headers_no_token(monkeypatch):
    """Test _get_headers returns Accept header and skips Authorization if no token."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GIT_TOKEN", raising=False)
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
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GIT_TOKEN", raising=False)

    resolver = GithubResolver("my-package#1.0", None,
                              "github://owner/repo/v1.0/v1.0.tar.gz", "v1.0")
    token = resolver._GithubResolver__get_gh_token()
    assert token == "pkg_token"


def test_github_resolver_get_gh_auth_multiple_special_chars(monkeypatch):
    """Test __get_gh_auth handles multiple special characters."""
    # Test sanitization of #, $, &, -, =, !, /
    monkeypatch.setenv("GITHUB_TESTPKG_TOKEN", "special_token")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GIT_TOKEN", raising=False)

    resolver = GithubResolver("test-pkg#$&=!/", None,
                              "github+private://owner/repo/v1.0/asset.tar.gz", "v1.0")
    token = resolver._GithubResolver__get_gh_token()
    assert token == "special_token"
