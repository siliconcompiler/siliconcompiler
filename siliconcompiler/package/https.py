import requests
import shutil
import tarfile
import zipfile

import os.path

from io import BytesIO
from urllib.parse import urlparse

from siliconcompiler.package import RemoteResolver


def get_resolver():
    return {
        "http": HTTPResolver,
        "https": HTTPResolver
    }


class HTTPResolver(RemoteResolver):
    def check_cache(self):
        return os.path.exists(self.cache_path)

    @property
    def download_url(self):
        data_url = self.source
        if data_url.endswith('/'):
            data_url = f"{data_url}{self.reference}.tar.gz"
        return data_url

    def resolve_remote(self):
        data_url = self.download_url

        headers = {}
        auth_token = os.environ.get('GIT_TOKEN', self.urlparse.username)
        if auth_token:
            headers['Authorization'] = f'token {auth_token}'
        if "github" in data_url:
            headers['Accept'] = 'application/octet-stream'

        self.logger.info(f'Downloading {self.name} data from {data_url}')

        response = requests.get(data_url, stream=True, headers=headers)
        if not response.ok:
            raise FileNotFoundError(f'Failed to download {self.name} data source.')

        os.makedirs(self.cache_path, exist_ok=True)

        fileobj = BytesIO(response.content)
        try:
            with tarfile.open(fileobj=fileobj, mode='r|gz') as tar_ref:
                tar_ref.extractall(path=self.cache_path)
        except tarfile.ReadError:
            fileobj.seek(0)
            # Try as zip
            with zipfile.ZipFile(fileobj) as zip_ref:
                zip_ref.extractall(path=self.cache_path)

        if 'github' in data_url and len(os.listdir(self.cache_path)) == 1:
            # Github inserts one folder at the highest level of the tar file
            # this compensates for this behavior
            gh_url = urlparse(data_url)

            repo = gh_url.path.split('/')[2]

            gh_ref = gh_url.path.split('/')[-1]
            if repo.endswith('.git'):
                gh_ref = self.reference
            elif gh_ref.endswith('.tar.gz'):
                gh_ref = gh_ref[0:-7]
            elif gh_ref.endswith('.tgz'):
                gh_ref = gh_ref[0:-4]
            else:
                gh_ref = gh_ref.split('.')[0]

            if gh_ref.startswith('v'):
                gh_ref = gh_ref[1:]

            github_folder = f"{repo}-{gh_ref}"

            if github_folder in os.listdir(self.cache_path):
                # This moves all files one level up
                git_path = os.path.join(self.cache_path, github_folder)
                for data_file in os.listdir(git_path):
                    shutil.move(os.path.join(git_path, data_file), self.cache_path)
                os.removedirs(git_path)
