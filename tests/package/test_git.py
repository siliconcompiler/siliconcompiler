import logging
import pytest

import os.path

from git import Repo, Actor
from pathlib import Path

from siliconcompiler.package.git import GitResolver
from siliconcompiler import Chip


@pytest.fixture(autouse=True)
def mock_git(monkeypatch):
    class MockGit:
        @staticmethod
        def checkout(*args, **kwargs):
            pass

    def clone(url, to_path, **kwargs):
        Path(to_path).mkdir(parents=True)
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


@pytest.mark.parametrize('path,ref', [
    ('git+https://github.com/siliconcompiler/siliconcompiler',
     'main'),
    ('git://github.com/siliconcompiler/siliconcompiler',
     'main'),
])
def test_dependency_path_download_git(path, ref, tmp_path):
    chip = Chip("dummy")
    chip.set("option", "cachedir", tmp_path)

    resolver = GitResolver("testgit", chip, path, ref)
    assert resolver.resolve() == Path(os.path.join(tmp_path, f"testgit-{ref}"))
    assert os.path.isfile(os.path.join(tmp_path, f"testgit-{ref}", "pyproject.toml"))


def test_git_path_git_ssh():
    resolver = GitResolver("testgit", Chip("dummy"),
                           "git+ssh://github.com/test_owner/test_repo", "main")
    assert resolver.git_path == "ssh://github.com/test_owner/test_repo"


def test_git_path_ssh():
    resolver = GitResolver("testgit", Chip("dummy"),
                           "ssh://github.com/test_owner/test_repo", "main")
    assert resolver.git_path == "ssh://github.com/test_owner/test_repo"


def test_git_path_default():
    resolver = GitResolver("testgit", Chip("dummy"),
                           "git://github.com/test_owner/test_repo", "main")
    assert resolver.git_path == "https://github.com/test_owner/test_repo"


def test_dirty_warning(caplog, tmp_path):
    chip = Chip("dummy")
    chip.logger = logging.getLogger()
    chip.set("option", "cachedir", tmp_path)

    resolver = GitResolver("testgit", chip, "git+ssh://github.com/test_owner/test_repo", "main")
    resolver.resolve()

    file = Path(resolver.cache_path).joinpath('file.txt')
    file.touch()

    resolver.resolve()

    assert "The repo of the cached data is dirty." in caplog.text

    file.unlink()
    assert not file.exists()
