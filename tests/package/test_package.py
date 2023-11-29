import siliconcompiler
from siliconcompiler import package
from pathlib import Path
import pytest
import logging
import os


def cache_path(path, ref, chip=None, quiet=True, cache=None):
    chip = chip or siliconcompiler.Chip('test')
    chip.set('option', 'cache', cache)

    if not cache:
        cache = Path.home().joinpath('.sc/cache')

    # Setting this manually as siliconcompiler_data package is currently not on pypi
    chip.register_package_source('siliconcompiler_data', path, ref)

    dependency_cache_path = Path(package.path(chip, 'siliconcompiler_data', quiet=quiet))

    if ref:
        dir_name = f'siliconcompiler_data-{ref}'
        assert Path(os.path.join(cache, dir_name)) == dependency_cache_path

    assert dependency_cache_path.exists()

    # Check if files got downloaded succesfully
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
        'main', chip=chip, quiet=False)
    assert "The repo of the cached data is dirty." in caplog.text

    file.unlink()
    assert not file.exists()
