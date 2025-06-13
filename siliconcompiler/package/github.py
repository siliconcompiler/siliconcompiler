import os

from github import Github, Auth
from github.GithubException import UnknownObjectException

from siliconcompiler.package.https import HTTPResolver


def get_resolver():
    return {
        "github": GithubResolver,
        "github+private": GithubResolver
    }


class GithubResolver(HTTPResolver):
    def __init__(self, name, root, source, reference=None):
        super().__init__(name, root, source, reference)

        if len(self.gh_path) != 4:
            raise ValueError(
                f"{self.source} is not in the proper form: "
                "<owner>/<repository>/<version>/<artifact>")

    @property
    def gh_path(self):
        return self.urlpath, *self.urlparse.path.split("/")[1:]

    @property
    def download_url(self):
        url_parts = self.gh_path

        repository = "/".join(url_parts[0:2])
        release = url_parts[2]
        artifact = url_parts[3]

        if self.urlscheme == "github+private":
            return self.__get_release_url(repository, release, artifact, True)

        try:
            return self.__get_release_url(repository, release, artifact, False)
        except UnknownObjectException:
            return self.__get_release_url(repository, release, artifact, True)

    def __get_release_url(self, repository, release, artifact, private: bool):
        if artifact == f"{release}.zip":
            return f"https://github.com/{repository}/archive/refs/tags/{release}.zip"
        if artifact == f"{release}.tar.gz":
            return f"https://github.com/{repository}/archive/refs/tags/{release}.tar.gz"

        repo = self.__gh(private).get_repo(repository)

        if not release:
            release = repo.get_latest_release().tag_name

        url = None
        for repo_release in repo.get_releases():
            if repo_release.tag_name == release:
                for asset in repo_release.assets:
                    if asset.name == artifact:
                        url = asset.url

        if not url:
            raise ValueError(f'Unable to find release asset: {repository}/{release}/{artifact}')

        return url

    def __get_gh_auth(self):
        token_name = self.name.upper()
        for tok in ('#', '$', '&', '-', '=', '!', '/'):
            token_name = token_name.replace(tok, '')

        search_env = (
            f'GITHUB_{token_name}_TOKEN',
            'GITHUB_TOKEN',
            'GIT_TOKEN'
        )

        token = None
        for env in search_env:
            token = os.environ.get(env, None)

            if token:
                break

        if not token:
            raise ValueError('Unable to determine authorization token for GitHub, '
                             'please set one of the following environmental variables: '
                             f'{", ".join(search_env)}')

        return token

    def __gh(self, private: bool) -> Github:
        if private:
            return Github(auth=Auth.Token(self.__get_gh_auth()))
        else:
            return Github()
