import requests
import shutil
import tarfile
import zipfile

import os.path

from fasteners import InterProcessLock
from io import BytesIO
from urllib.parse import urlparse

from siliconcompiler import SiliconCompilerError
from siliconcompiler.package import get_download_cache_path
from siliconcompiler.package import aquire_data_lock, release_data_lock


def get_resolver(url):
    if url.scheme in ("http", "https"):
        return http_resolver

    return None


def http_resolver(chip, package, path, ref, url, fetch):
    data_path, data_path_lock = get_download_cache_path(chip, package, ref)

    if not fetch:
        return data_path, False

    # Acquire lock
    data_lock = InterProcessLock(data_path_lock)
    aquire_data_lock(data_path, data_lock)

    if os.path.exists(data_path):
        release_data_lock(data_lock)
        return data_path, False

    return _http_resolver(chip, package, path, ref, url, data_lock)


def _http_resolver(chip, package, path, ref, url, data_lock):
    data_path, _ = get_download_cache_path(chip, package, ref)

    extract_from_url(chip, package, path, ref, url, data_path)

    release_data_lock(data_lock)

    return data_path, True


def extract_from_url(chip, package, path, ref, url, data_path):
    data_url = path
    headers = {}
    if os.environ.get('GIT_TOKEN') or url.username:
        headers['Authorization'] = f'token {os.environ.get("GIT_TOKEN") or url.username}'
    if "github" in data_url:
        headers['Accept'] = 'application/octet-stream'
    data_url = path
    if data_url.endswith('/'):
        data_url = f"{data_url}{ref}.tar.gz"
    chip.logger.info(f'Downloading {package} data from {data_url}')
    response = requests.get(data_url, stream=True, headers=headers)
    if not response.ok:
        raise SiliconCompilerError(f'Failed to download {package} data source.', chip=chip)

    fileobj = BytesIO(response.content)
    try:
        with tarfile.open(fileobj=fileobj, mode='r|gz') as tar_ref:
            tar_ref.extractall(path=data_path)
    except tarfile.ReadError:
        fileobj.seek(0)
        # Try as zip
        with zipfile.ZipFile(fileobj) as zip_ref:
            zip_ref.extractall(path=data_path)

    if 'github' in url.netloc and len(os.listdir(data_path)) == 1:
        # Github inserts one folder at the highest level of the tar file
        # this compensates for this behavior
        gh_url = urlparse(data_url)

        repo = gh_url.path.split('/')[2]

        gh_ref = gh_url.path.split('/')[-1]
        if repo.endswith('.git'):
            gh_ref = ref
        elif gh_ref.endswith('.tar.gz'):
            gh_ref = gh_ref[0:-7]
        elif gh_ref.endswith('.tgz'):
            gh_ref = gh_ref[0:-4]
        else:
            gh_ref = gh_ref.split('.')[0]

        if gh_ref.startswith('v'):
            gh_ref = gh_ref[1:]

        github_folder = f"{repo}-{gh_ref}"

        if github_folder in os.listdir(data_path):
            # This moves all files one level up
            git_path = os.path.join(data_path, github_folder)
            for data_file in os.listdir(git_path):
                shutil.move(os.path.join(git_path, data_file), data_path)
            os.removedirs(git_path)
