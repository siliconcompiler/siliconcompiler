import siliconcompiler
from siliconcompiler import package
from pathlib import Path
import pytest
import logging
import os


def cache_path(path, ref, chip=None, cache=None):
    chip = chip or siliconcompiler.Chip('test')
    chip.set('option', 'cachedir', cache)

    if not cache:
        cache = Path.home().joinpath('.sc/cache')

    # Setting this manually as siliconcompiler_data package is currently not on pypi
    chip.register_source('siliconcompiler_data', path, ref)

    dependency_cache_path = Path(package.path(chip, 'siliconcompiler_data'))

    if ref:
        dir_name = f'siliconcompiler_data-{ref}'
        assert Path(os.path.join(cache, dir_name)) == dependency_cache_path

    assert dependency_cache_path.exists()

    # Check if files got downloaded successfully
    assert dependency_cache_path.joinpath('requirements.txt').is_file()
    return dependency_cache_path


@pytest.mark.timeout(300)
@pytest.mark.parametrize('path,ref', [
    ('git+https://github.com/siliconcompiler/siliconcompiler',
     'main'),
    ('git://github.com/siliconcompiler/siliconcompiler',
     'main'),
    ('https://github.com/siliconcompiler/siliconcompiler/archive/',
     '938df309b4803fd79b10de6d3c7d7aa4645c39f5'),
    ('https://github.com/siliconcompiler/siliconcompiler/archive/refs/heads/main.tar.gz',
     'version-1')
])
def test_dependency_path_download(path, ref):
    cache_path(path, ref)


# Only run on tools CI because only that has ssh auth set up
@pytest.mark.eda
@pytest.mark.parametrize('path,ref', [
    ('git://github.com/siliconcompiler/siliconcompiler',
     'main'),
])
@pytest.mark.timeout(300)
def test_package_path_user_cache(path, ref):
    cache_path(path, ref, cache=os.path.abspath('test_cache'))


# Only run on tools CI because only that has ssh auth set up
@pytest.mark.eda
@pytest.mark.parametrize('path,ref', [
    ('git+ssh://git@github.com/siliconcompiler/siliconcompiler',
     'main')
])
@pytest.mark.timeout(300)
def test_dependency_path_ssh(path, ref):
    cache_path(path, ref)


@pytest.mark.timeout(300)
@pytest.mark.parametrize('prefix', ['file://', ''])
def test_dependency_path_local_prefix(prefix):
    local_dependency_cache_path = cache_path(
        'git+https://github.com/siliconcompiler/siliconcompiler',
        'main')
    cache_path(f'{prefix}{str(local_dependency_cache_path)}', '')


@pytest.mark.timeout(300)
def test_dependency_path_dirty_warning(caplog):
    local_dependency_cache_path = cache_path(
        'git+https://github.com/siliconcompiler/siliconcompiler',
        'main')

    file = Path(local_dependency_cache_path).joinpath('file.txt')
    file.touch()

    chip = siliconcompiler.Chip('test')
    chip.logger = logging.getLogger()
    local_dependency_cache_path = cache_path(
        'git+https://github.com/siliconcompiler/siliconcompiler',
        'main', chip=chip)
    assert "The repo of the cached data is dirty." in caplog.text

    file.unlink()
    assert not file.exists()


def test_package_with_import():
    chip = siliconcompiler.Chip('test')

    lib = siliconcompiler.Library(chip, 'lib')
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
    chip = siliconcompiler.Chip('')
    lib = siliconcompiler.Library(chip, "test", package=(
        "test", "path_to_test"))

    assert lib.get('package', 'source', 'test', 'path') == "path_to_test"
    assert lib.get('package', 'source', 'test', 'ref') is None


def test_register_source_tuple_3():
    chip = siliconcompiler.Chip('')
    lib = siliconcompiler.Library(chip, "test", package=(
        "test", "path_to_test", "ref"))

    assert lib.get('package', 'source', 'test', 'path') == "path_to_test"
    assert lib.get('package', 'source', 'test', 'ref') == "ref"


def test_register_source_tuple_error():
    chip = siliconcompiler.Chip('')
    with pytest.raises(ValueError):
        siliconcompiler.Library(chip, "test", package=("test",))


def test_register_source_dict_path():
    chip = siliconcompiler.Chip('')
    lib = siliconcompiler.Library(chip, "test", package={
        "test": {"path": "path_to_test"}})

    assert lib.get('package', 'source', 'test', 'path') == "path_to_test"
    assert lib.get('package', 'source', 'test', 'ref') is None


def test_register_source_dict_ref():
    chip = siliconcompiler.Chip('')
    lib = siliconcompiler.Library(chip, "test", package={
        "test": {"path": "path_to_test", "ref": "ref"}})

    assert lib.get('package', 'source', 'test', 'path') == "path_to_test"
    assert lib.get('package', 'source', 'test', 'ref') == "ref"


def test_register_source_dict_error():
    chip = siliconcompiler.Chip('')
    with pytest.raises(ValueError):
        siliconcompiler.Library(chip, "test", package={
            "test": {"ref": "ref"}})


def test_register_source_int():
    chip = siliconcompiler.Chip('')
    with pytest.raises(ValueError):
        siliconcompiler.Library(chip, "test", package=4)
