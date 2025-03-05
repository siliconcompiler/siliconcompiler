import siliconcompiler
from siliconcompiler import package
from pathlib import Path
import pytest
import logging
import os
import responses
import re
from git import Repo, Actor


@pytest.fixture(autouse=True)
def mock_git(monkeypatch):
    class mockGit:
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

        repo.git = mockGit

        return repo

    monkeypatch.setattr("git.Repo.clone_from", clone)


def cache_path(path, ref, chip=None, cache=None):
    chip = chip or siliconcompiler.Chip('test')
    chip.set('option', 'cachedir', cache)

    if not cache:
        cache = Path.home().joinpath('.sc/cache')

    assert "siliconcompiler_data" not in chip._packages

    # Setting this manually as siliconcompiler_data package is currently not on pypi
    chip.register_source('siliconcompiler_data', path, ref)

    assert "siliconcompiler_data" not in chip._packages

    dependency_cache_path = Path(package.path(chip, 'siliconcompiler_data'))

    if ref:
        dir_name = f'siliconcompiler_data-{ref}'
        assert Path(os.path.join(cache, dir_name)) == dependency_cache_path

    assert dependency_cache_path.exists()

    # Check if files got downloaded successfully
    assert dependency_cache_path.joinpath('pyproject.toml').is_file()

    assert "siliconcompiler_data" in chip._packages

    return dependency_cache_path


@pytest.mark.parametrize('path,ref', [
    ('https://github.com/siliconcompiler/siliconcompiler/archive/',
     '938df309b4803fd79b10de6d3c7d7aa4645c39f5'),
    ('https://github.com/siliconcompiler/siliconcompiler/archive/refs/heads/main.tar.gz',
     'version-1')
])
@responses.activate
def test_dependency_path_download_http(datadir, path, ref, tmp_path):
    with open(os.path.join(datadir, 'https.tar.gz'), "rb") as f:
        responses.add(
            responses.GET,
            re.compile(r"https://github.com/siliconcompiler/siliconcompiler/.*\.tar.gz"),
            body=f.read(),
            status=200,
            content_type="application/x-gzip"
        )
    cache_path(path, ref, cache=tmp_path)


@pytest.mark.parametrize('path,ref', [
    ('git+https://github.com/siliconcompiler/siliconcompiler',
     'main'),
    ('git://github.com/siliconcompiler/siliconcompiler',
     'main'),
])
def test_dependency_path_download_git(path, ref, tmp_path):
    cache_path(path, ref, cache=tmp_path)


@pytest.mark.parametrize('path,ref', [
    ('git://github.com/siliconcompiler/siliconcompiler',
     'main'),
])
def test_package_path_user_cache(path, ref):
    cache_path(path, ref, cache=os.path.abspath('test_cache'))


def test_package_path_user_cache_not_supported():
    with pytest.raises(ValueError, match="nosupport://help.me/file is not supported"):
        cache_path("nosupport://help.me/file", None, cache=os.path.abspath('test_cache'))


@pytest.mark.parametrize('path,ref', [
    ('git+ssh://git@github.com/siliconcompiler/siliconcompiler',
     'main')
])
def test_dependency_path_ssh(path, ref, tmp_path):
    cache_path(path, ref, cache=tmp_path)


@pytest.mark.parametrize('prefix', ['file://', ''])
def test_dependency_path_local_prefix(prefix, tmp_path):
    local_dependency_cache_path = cache_path(
        'git+https://github.com/siliconcompiler/siliconcompiler',
        'main',
        cache=tmp_path)
    cache_path(f'{prefix}{str(local_dependency_cache_path)}', '')


def test_dependency_path_dirty_warning(caplog, tmp_path):
    local_dependency_cache_path = cache_path(
        'git+https://github.com/siliconcompiler/siliconcompiler',
        'main',
        cache=tmp_path)

    file = Path(local_dependency_cache_path).joinpath('file.txt')
    file.touch()

    chip = siliconcompiler.Chip('test')
    chip.logger = logging.getLogger()
    local_dependency_cache_path = cache_path(
        'git+https://github.com/siliconcompiler/siliconcompiler',
        'main', chip=chip, cache=tmp_path)
    assert "The repo of the cached data is dirty." in caplog.text

    file.unlink()
    assert not file.exists()


def test_package_with_import():
    chip = siliconcompiler.Chip('test')

    lib = siliconcompiler.Library('lib')
    lib.register_source('test-source', 'path', 'ref')

    assert 'test-source' not in chip.getkeys('package', 'source')
    chip.use(lib)
    assert 'test-source' in chip.getkeys('package', 'source')


def test_package_with_env_var(monkeypatch):
    chip = siliconcompiler.Chip('test')
    chip.register_source('test-source', '$TEST_HOME')

    os.mkdir('test1')
    monkeypatch.setenv("TEST_HOME", 'test1')
    assert os.path.basename(package.path(chip, 'test-source')) == 'test1'


def test_path_from_python_without_append():
    chip = siliconcompiler.Chip('test')
    path = package.path_from_python(chip, "siliconcompiler.apps")

    assert path == os.path.join(chip.scroot, "apps")


def test_path_from_python_with_append():
    chip = siliconcompiler.Chip('test')
    path = package.path_from_python(chip, "siliconcompiler", "apps")

    assert path == os.path.join(chip.scroot, "apps")


@pytest.mark.parametrize('is_local', [True, False])
def test_register_python_data_source(monkeypatch, is_local):
    chip = siliconcompiler.Chip('test')

    def dummy_func(module_name):
        return is_local
    monkeypatch.setattr(package, "is_python_module_editable", dummy_func)

    local_path = "python://siliconcompiler"
    remote_path = "git+https://testing.com/sc_test.git"
    package.register_python_data_source(
        chip,
        "sc_test",
        "siliconcompiler",
        remote_path
    )

    if is_local:
        expect = local_path
    else:
        expect = remote_path

    path = chip.get("package", "source", "sc_test", "path")

    assert path == expect


def test_register_python_data_source_with_append(monkeypatch):
    chip = siliconcompiler.Chip('test')

    def dummy_func(module_name):
        return True
    monkeypatch.setattr(package, "is_python_module_editable", dummy_func)

    expect = os.path.join(chip.scroot, "apps")
    package.register_python_data_source(
        chip,
        "sc_test",
        "siliconcompiler",
        "git+https://testing.com/sc_test.git",
        python_module_path_append="apps"
    )

    path = chip.get("package", "source", "sc_test", "path")

    assert path == expect


def test_register_source_tuple_2():
    lib = siliconcompiler.Library("test", package=(
        "test", "path_to_test"))

    assert lib.get('package', 'source', 'test', 'path') == "path_to_test"
    assert lib.get('package', 'source', 'test', 'ref') is None


def test_register_source_tuple_3():
    lib = siliconcompiler.Library("test", package=(
        "test", "path_to_test", "ref"))

    assert lib.get('package', 'source', 'test', 'path') == "path_to_test"
    assert lib.get('package', 'source', 'test', 'ref') == "ref"


def test_register_source_tuple_error():
    with pytest.raises(ValueError):
        siliconcompiler.Library("test", package=("test",))


def test_register_source_dict_path():
    lib = siliconcompiler.Library("test", package={
        "test": {"path": "path_to_test"}})

    assert lib.get('package', 'source', 'test', 'path') == "path_to_test"
    assert lib.get('package', 'source', 'test', 'ref') is None


def test_register_source_dict_ref():
    lib = siliconcompiler.Library("test", package={
        "test": {"path": "path_to_test", "ref": "ref"}})

    assert lib.get('package', 'source', 'test', 'path') == "path_to_test"
    assert lib.get('package', 'source', 'test', 'ref') == "ref"


def test_register_source_dict_error():
    with pytest.raises(ValueError):
        siliconcompiler.Library("test", package={
            "test": {"ref": "ref"}})


def test_register_source_int():
    with pytest.raises(ValueError):
        siliconcompiler.Library("test", package=4)
