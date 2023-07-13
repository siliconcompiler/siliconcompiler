import os
import requests
import tarfile


def path(chip, package):
    """
    Compute dependency data path

    Additionally cache dependency data if possible

    Parameters:
    arg1 (package): Package with dependency source info
        package.dependency (dict):
            Mandatory keys:
            'path': '/path/on/network/drive',
            or
            'archive_url': e.g. 'https://github.com/xyz/xyz/archive/'
            'commit_id': e.g. '3b94aa80506d25d5388131e9f2ecfcf4025ca866',
            'project_name': e.g. 'freepdk',
            or
            'full_url': e.g. 'https://zeroasic.com/xyz.tar.gz',
            'project_id': e.g. 'your-project-id-123',

            Additional keys:
            'rel_data_path': 'data/path/inside/archive/or/directory',
            'type': e.g. 'pdk'

    Returns:
    string: Location of dependency data

    """

    dependency = package.dependency
    dependency_type = dependency.get('type', 'dependency')
    # check network drive for dependency data
    if dependency.get('path') and os.path.exists(dependency['path']):
        chip.logger.info(f'Found network {dependency_type} data at {dependency["path"]}')
        return dependency['path']

    # location of the python package
    package_path = os.path.dirname(os.path.realpath(package.__file__))
    dependency_url = dependency.get('full_url')
    if not dependency_url:
        if dependency.get('archive_url') and dependency.get('commit_id'):
            dependency_url = dependency['archive_url'] + dependency['commit_id'] + '.tar.gz'
    project_id = dependency.get('project_id')
    if not project_id:
        if dependency.get('project_name') and dependency.get('commit_id'):
            project_id = dependency['project_name'] + '-' + dependency['commit_id']
    if not dependency_url or not project_id:
        chip.error(f'Could not find {dependency_type} data in package {package.__name__}')
    cache_path = os.path.join(package_path, project_id, dependency.get('rel_data_path', ''))

    # check cached dependency data
    if os.path.exists(cache_path):
        chip.logger.info(f'Found cached {dependency_type} data at {cache_path}')
        return cache_path
    # download dependency data
    chip.logger.info(f'Downloading {dependency_type} data from {dependency_url}')
    response = requests.get(dependency_url, stream=True)
    if not response.ok:
        chip.error(f'Failed to download {dependency_type}')
    file = tarfile.open(fileobj=response.raw, mode='r|gz')
    # extract only the data files of the dependency commit
    try:
        dependency_filter = (
            lambda member, path: member
            if member.name.startswith(os.path.join(project_id, dependency.get('rel_data_path', '')))
            else None
        )
        file.extractall(path=package_path, filter=dependency_filter)
    except TypeError:
        chip.logger.info(f'Filtering {dependency_type}.tar.gz not supported on Python <3.11.4')
        chip.logger.info(f'Extracting full {dependency_type} repository instead')
        file.extractall(path=package_path)
    if os.path.exists(cache_path):
        chip.logger.info(f'Saved {dependency_type} data to {cache_path}')
        return cache_path
    chip.error(f'Extracting {dependency_type} data to {cache_path} failed')
