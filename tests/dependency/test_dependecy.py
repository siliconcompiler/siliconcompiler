import siliconcompiler
from siliconcompiler import dependency
from pathlib import Path
import pytest


def dependency_cache_path(path, name, commitid):
    chip = siliconcompiler.Chip('test')

    # Setting this manually as siliconcompiler_data package is currently not on pypi
    chip.set('dependency', 'siliconcompiler_data', 'path', path)
    chip.set('dependency', 'siliconcompiler_data', 'name', name)
    chip.set('dependency', 'siliconcompiler_data', 'commitid', commitid)

    dependency_cache_path = Path(dependency.path(chip, 'siliconcompiler_data'))

    if name:
        dir_name = f'{name}-{commitid}' if commitid else name
        assert Path.home().joinpath(f'.sc/cache/{dir_name}') == dependency_cache_path

    assert dependency_cache_path.exists()

    # Check if files got downloaded succesfully
    assert dependency_cache_path.joinpath('requirements.txt').is_file()
    return dependency_cache_path


@pytest.mark.parametrize('path,name,commitid', [
    ('git+https://github.com/siliconcompiler/siliconcompiler',
     'siliconcompiler_git_https',
     'main'),
    ('git://github.com/siliconcompiler/siliconcompiler',
     'siliconcompiler_git',
     'main'),
    ('git+ssh://git@github.com/siliconcompiler/siliconcompiler',
     'siliconcompiler_git_ssh',
     'main'),
    ('ssh://git@github.com/siliconcompiler/siliconcompiler',
     'siliconcompiler_ssh',
     'main'),
    ('https://github.com/siliconcompiler/siliconcompiler/archive/',
     'siliconcompiler_https_commitid',
     '938df309b4803fd79b10de6d3c7d7aa4645c39f5'),
    ('https://github.com/siliconcompiler/siliconcompiler/archive/refs/heads/main.tar.gz',
     'siliconcompiler_https',
     '')
])
def test_dependency_path_download(path, name, commitid):
    dependency_cache_path(path, name, commitid)


@pytest.mark.parametrize('prefix', ['file://', ''])
def test_dependency_path_local_prefix(prefix):
    local_dependency_cache_path = dependency_cache_path(
        'git+https://github.com/siliconcompiler/siliconcompiler',
        'siliconcompiler_file',
        'main')
    dependency_cache_path(f'{prefix}{str(local_dependency_cache_path)}', '', '')
