import siliconcompiler
from siliconcompiler import dependency
from pathlib import Path
import pytest


def dependency_cache_path(path, ref):
    chip = siliconcompiler.Chip('test')

    # Setting this manually as siliconcompiler_data package is currently not on pypi
    chip.set('dependency', 'siliconcompiler_data', 'path', path)
    chip.set('dependency', 'siliconcompiler_data', 'ref', ref)

    dependency_cache_path = Path(dependency.path(chip, 'siliconcompiler_data'))

    if ref:
        dir_name = f'siliconcompiler_data-{ref}'
        assert Path.home().joinpath(f'.sc/cache/{dir_name}') == dependency_cache_path

    assert dependency_cache_path.exists()

    # Check if files got downloaded succesfully
    assert dependency_cache_path.joinpath('requirements.txt').is_file()
    return dependency_cache_path


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
    dependency_cache_path(path, ref)


# Only run on tools CI because only that has ssh auth set up
@pytest.mark.eda
@pytest.mark.parametrize('path,ref', [
    ('git+ssh://git@github.com/siliconcompiler/siliconcompiler',
     'main'),
    ('ssh://git@github.com/siliconcompiler/siliconcompiler',
     'main')
])
def test_dependency_path_ssh(path, ref):
    dependency_cache_path(path, ref)


@pytest.mark.parametrize('prefix', ['file://', ''])
def test_dependency_path_local_prefix(prefix):
    local_dependency_cache_path = dependency_cache_path(
        'git+https://github.com/siliconcompiler/siliconcompiler',
        'main')
    dependency_cache_path(f'{prefix}{str(local_dependency_cache_path)}', '')
