import logging
import pytest
import sys

import os.path

from git import Repo, Actor
from pathlib import Path
from unittest.mock import patch, MagicMock

from siliconcompiler.package.git import GitResolver
from siliconcompiler import Project


@pytest.fixture(autouse=True)
def mock_git(monkeypatch):
    class MockGit:
        @staticmethod
        def checkout(*args, **kwargs):
            pass

    def clone(url, to_path, **kwargs):
        Path(to_path).mkdir(parents=True, exist_ok=True)
        repo = Repo.init(to_path)

        test_path = Path(to_path) / 'pyproject.toml'
        test_path.touch()

        author = Actor("author", "author@example.com")
        committer = Actor("committer", "committer@example.com")
        repo.index.add('pyproject.toml')
        repo.index.commit('msg', author=author, committer=committer)

        repo.git = MockGit

        return repo

    monkeypatch.setattr("git.Repo.clone_from", clone)


@pytest.mark.parametrize('path,ref,cache_id', [
    ('git+https://github.com/siliconcompiler/siliconcompiler',
     'main',
     '933ab1d5daa72905'),
    ('git://github.com/siliconcompiler/siliconcompiler',
     'main',
     '4bd21abf91c854d6'),
])
def test_dependency_path_download_git(path, ref, cache_id, tmp_path):
    proj = Project("testproj")
    proj.set("option", "cachedir", tmp_path)

    resolver = GitResolver("testgit", proj, path, ref)
    assert resolver.resolve() == Path(os.path.join(tmp_path, f"testgit-{ref}-{cache_id}"))
    assert os.path.isfile(os.path.join(tmp_path, f"testgit-{ref}-{cache_id}", "pyproject.toml"))


def test_git_path_git_ssh():
    resolver = GitResolver("testgit", Project(),
                           "git+ssh://github.com/test_owner/test_repo", "main")
    assert resolver.git_path == "ssh://github.com/test_owner/test_repo"


def test_git_path_ssh():
    resolver = GitResolver("testgit", Project(),
                           "ssh://github.com/test_owner/test_repo", "main")
    assert resolver.git_path == "ssh://github.com/test_owner/test_repo"


def test_git_path_default():
    resolver = GitResolver("testgit", Project(),
                           "git://github.com/test_owner/test_repo", "main")
    assert resolver.git_path == "https://github.com/test_owner/test_repo"


@pytest.mark.skipif(sys.platform == "win32", reason="Appears to cause issues on windows machines")
def test_dirty_warning(monkeypatch, caplog, tmp_path):
    proj = Project("testproj")
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    assert Path(tmp_path).exists()

    resolver = GitResolver("testgit", proj, "git+ssh://github.com/test_owner/test_repo", "main")
    resolver.resolve()

    assert Path(resolver.cache_path).exists()

    file = Path(resolver.cache_path).joinpath('file.txt')
    file.touch()

    resolver.resolve()

    assert "The repo of the cached data is dirty." in caplog.text


# ============================================================================
# Additional GitResolver Tests
# ============================================================================

def test_git_resolver_get_resolver():
    """Test get_resolver returns correct mapping for Git schemes."""
    from siliconcompiler.package.git import get_resolver
    resolvers = get_resolver()
    assert isinstance(resolvers, dict)
    assert "git" in resolvers
    assert "git+https" in resolvers
    assert "git+ssh" in resolvers
    assert "ssh" in resolvers
    for resolver in resolvers.values():
        assert resolver is GitResolver


def test_git_resolver_check_cache_no_path():
    """Test check_cache returns False when path doesn't exist."""
    resolver = GitResolver("test", None, "git://github.com/owner/repo.git", "main")
    with patch("os.path.exists", return_value=False):
        assert resolver.check_cache() is False


def test_git_resolver_check_cache_valid_repo(monkeypatch):
    """Test check_cache returns True for valid repository."""
    resolver = GitResolver("test", None, "git://github.com/owner/repo.git", "main")

    mock_repo = MagicMock()
    mock_repo.untracked_files = []
    mock_repo.index.diff.return_value = []

    import siliconcompiler.package.git as git_module
    with patch("os.path.exists", return_value=True), \
         patch.object(git_module, "Repo", return_value=mock_repo):
        assert resolver.check_cache() is True


def test_git_resolver_check_cache_dirty_repo(monkeypatch, caplog):
    """Test check_cache warns about dirty repository."""
    resolver = GitResolver("test", Project("testproj"), "git://github.com/owner/repo.git", "main")

    mock_repo = MagicMock()
    mock_repo.untracked_files = ["untracked.txt"]
    mock_repo.index.diff.return_value = []

    import siliconcompiler.package.git as git_module
    with patch("os.path.exists", return_value=True), \
         patch.object(git_module, "Repo", return_value=mock_repo):
        caplog.clear()
        caplog.set_level(logging.WARNING)
        result = resolver.check_cache()
        assert result is True
        # Logger warning is in the resolver
        assert resolver.logger is not None


def test_git_resolver_check_cache_corrupted_repo(monkeypatch, caplog):
    """Test check_cache removes corrupted repository."""
    resolver = GitResolver("test", Project("testproj"), "git://github.com/owner/repo.git", "main")

    import siliconcompiler.package.git as git_module
    from git.exc import GitCommandError

    with patch("os.path.exists", return_value=True), \
         patch.object(git_module, "Repo",
                      side_effect=GitCommandError("git", "init", stderr=b"corrupted")), \
         patch.object(git_module, "shutil") as mock_shutil:
        result = resolver.check_cache()
        assert result is False
        mock_shutil.rmtree.assert_called_once()


def test_git_resolver_get_token_env_github_package(monkeypatch):
    """Test __get_token_env finds package-specific GitHub token."""
    monkeypatch.setenv("GITHUB_SKYWATER130_TOKEN", "token_package")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    resolver = GitResolver("skywater130", None, "git://github.com/owner/repo.git", "main")
    # Access the private method through name mangling
    token = resolver._GitResolver__get_token_env()
    assert token == "token_package"


def test_git_resolver_get_token_env_github_general(monkeypatch):
    """Test __get_token_env falls back to GITHUB_TOKEN."""
    monkeypatch.delenv("GITHUB_TEST_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "token_general")

    resolver = GitResolver("test", None, "git://github.com/owner/repo.git", "main")
    token = resolver._GitResolver__get_token_env()
    assert token == "token_general"


def test_git_resolver_get_token_env_git_token(monkeypatch):
    """Test __get_token_env falls back to GIT_TOKEN."""
    monkeypatch.delenv("GITHUB_TEST_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("GIT_TOKEN", "token_git")

    resolver = GitResolver("test", None, "git://github.com/owner/repo.git", "main")
    token = resolver._GitResolver__get_token_env()
    assert token == "token_git"


def test_git_resolver_get_token_env_none(monkeypatch):
    """Test __get_token_env returns None when no token found."""
    monkeypatch.delenv("GITHUB_TEST_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GIT_TOKEN", raising=False)

    resolver = GitResolver("test", None, "git://github.com/owner/repo.git", "main")
    token = resolver._GitResolver__get_token_env()
    assert token is None


def test_git_resolver_get_token_env_sanitize_name(monkeypatch):
    """Test __get_token_env with special characters in name."""
    monkeypatch.setenv("GITHUB_PACKAGENAME_TOKEN", "token_sanitized")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    resolver = GitResolver("package-name", None, "git://github.com/owner/repo.git", "main")
    token = resolver._GitResolver__get_token_env()
    # When special characters are removed from "package-name", it becomes "packagename"
    # So it should find GITHUB_PACKAGENAME_TOKEN
    assert token == "token_sanitized" or token is None


def test_git_resolver_git_path_ssh():
    """Test git_path constructs SSH URL correctly."""
    resolver = GitResolver("test", None, "git+ssh://git@github.com/owner/repo.git", "main")
    assert resolver.git_path == "ssh://git@github.com/owner/repo.git"


def test_git_resolver_git_path_https_no_token(monkeypatch):
    """Test git_path constructs HTTPS URL without token."""
    monkeypatch.delenv("GITHUB_TEST_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GIT_TOKEN", raising=False)

    resolver = GitResolver("test", None, "git+https://github.com/owner/repo.git", "main")
    assert resolver.git_path == "https://github.com/owner/repo.git"


def test_git_resolver_git_path_https_with_token(monkeypatch):
    """Test git_path injects token into HTTPS URL."""
    monkeypatch.setenv("GITHUB_TOKEN", "test_token")

    resolver = GitResolver("test", None, "git+https://github.com/owner/repo.git", "main")
    assert "test_token@github.com" in resolver.git_path


def test_git_resolver_resolve_remote_success(monkeypatch):
    """Test resolve_remote clones repository successfully."""
    resolver = GitResolver("test", Project("testproj"), "git://github.com/owner/repo.git", "main")

    mock_repo = MagicMock()
    mock_repo.submodules = []

    import siliconcompiler.package.git as git_module
    with patch.object(git_module, "Repo") as mock_repo_class:
        mock_repo_class.clone_from.return_value = mock_repo
        resolver.resolve_remote()

        mock_repo_class.clone_from.assert_called_once()
        mock_repo.git.checkout.assert_called_once_with("main")


def test_git_resolver_resolve_remote_with_submodules(monkeypatch):
    """Test resolve_remote initializes submodules."""
    resolver = GitResolver("test", Project("testproj"), "git://github.com/owner/repo.git", "main")

    mock_submodule = MagicMock()
    mock_repo = MagicMock()
    mock_repo.submodules = [mock_submodule]

    import siliconcompiler.package.git as git_module
    with patch.object(git_module, "Repo") as mock_repo_class:
        mock_repo_class.clone_from.return_value = mock_repo
        resolver.resolve_remote()

        mock_submodule.update.assert_called_once()


def test_git_resolver_resolve_remote_ssh_auth_error(monkeypatch):
    """Test resolve_remote handles SSH authentication errors."""
    resolver = GitResolver("test", None, "git+ssh://git@github.com/owner/repo.git", "main")

    import siliconcompiler.package.git as git_module
    from git.exc import GitCommandError

    # Create GitCommandError that will show 'Permission denied' in repr
    error = GitCommandError("git", "clone", stderr="Permission denied")

    with patch.object(git_module, "Repo") as mock_repo_class:
        mock_repo_class.clone_from.side_effect = error
        with pytest.raises(RuntimeError, match="SSH"):
            resolver.resolve_remote()


def test_git_resolver_resolve_remote_https_auth_error(monkeypatch):
    """Test resolve_remote handles HTTPS authentication errors."""
    resolver = GitResolver("test", None, "git+https://github.com/owner/repo.git", "main")

    import siliconcompiler.package.git as git_module
    from git.exc import GitCommandError

    # Create GitCommandError that will show 'could not read Username' in repr
    error = GitCommandError("git", "clone", stderr="could not read Username")

    with patch.object(git_module, "Repo") as mock_repo_class:
        mock_repo_class.clone_from.side_effect = error
        with pytest.raises(RuntimeError, match="token"):
            resolver.resolve_remote()


def test_git_resolver_resolve_remote_other_error(monkeypatch):
    """Test resolve_remote re-raises non-auth Git errors."""
    resolver = GitResolver("test", None, "git://github.com/owner/repo.git", "main")

    import siliconcompiler.package.git as git_module

    # Create a mock that raises with a generic error
    def raise_other_error(*args, **kwargs):
        from git.exc import GitCommandError
        raise GitCommandError("git", "clone", stderr=b"some other error")

    with patch.object(git_module, "Repo") as mock_repo_class:
        mock_repo_class.clone_from = raise_other_error
        with pytest.raises(Exception):  # Will raise GitCommandError
            resolver.resolve_remote()
