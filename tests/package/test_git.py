import logging
import pytest
import sys

import os.path

from git import Repo, Actor
from pathlib import Path

from siliconcompiler.project import Project
from siliconcompiler.package.git import GitResolver


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
