import pytest

from unittest.mock import patch

from siliconcompiler.project import Project
from siliconcompiler.package.github import GithubResolver


def test_init_incorrect():
    with pytest.raises(ValueError,
                       match="'github://this' is not in the proper form: github://"
                             "<owner>/<repository>/<version>/<artifact>"):
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
