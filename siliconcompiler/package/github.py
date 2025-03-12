import os
from fasteners import InterProcessLock
from github import Github, Auth
from github.GithubException import UnknownObjectException
from urllib.parse import urlparse
from siliconcompiler.package import get_download_cache_path
from siliconcompiler.package import aquire_data_lock, release_data_lock
from siliconcompiler.package.https import _http_resolver


def get_resolver(url):
    if url.scheme in ("github",):
        return github_any_resolver
    if url.scheme in ("github+private",):
        return github_private_resolver
    return None


def github_any_resolver(chip, package, path, ref, url, fetch):
    data_path, data_path_lock = get_download_cache_path(chip, package, ref)

    if not fetch:
        return data_path, False

    # Acquire lock
    data_lock = InterProcessLock(data_path_lock)
    aquire_data_lock(data_path, data_lock)

    if os.path.exists(data_path):
        release_data_lock(data_lock)
        return data_path, False

    try:
        return _github_resolver(chip, package, path, ref, url, data_lock)
    except UnknownObjectException:
        return github_private_resolver(chip, package, path, ref, url, fetch, data_lock=data_lock)


def github_private_resolver(chip, package, path, ref, url, fetch, data_lock=None):
    data_path, data_path_lock = get_download_cache_path(chip, package, ref)

    if not fetch:
        return data_path, False

    if not data_lock:
        # Acquire lock
        data_lock = InterProcessLock(data_path_lock)
        aquire_data_lock(data_path, data_lock)

    if os.path.exists(data_path):
        release_data_lock(data_lock)
        return data_path, False

    gh = Github(auth=Auth.Token(__get_github_auth_token(package)))

    return _github_resolver(chip, package, path, ref, url, data_lock, gh=gh)


def _github_resolver(chip, package, path, ref, url, data_lock, gh=None):
    if not gh:
        gh = Github()

    url_parts = (url.netloc, *url.path.split("/")[1:])

    if len(url_parts) != 4:
        raise ValueError(
            f"{path} is not in the proper form: <owner>/<repository>/<version>/<artifact>")

    repository = "/".join(url_parts[0:2])
    release = url_parts[2]
    artifact = url_parts[3]

    release_url = __get_release_url(gh, repository, release, artifact)

    return _http_resolver(chip, package, release_url, ref, urlparse(release_url), data_lock)


def __get_release_url(gh, repository, release, artifact):
    if artifact == f"{release}.zip":
        return f"https://github.com/{repository}/archive/refs/tags/{release}.zip"
    if artifact == f"{release}.tar.gz":
        return f"https://github.com/{repository}/archive/refs/tags/{release}.tar.gz"

    repo = gh.get_repo(repository)

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


def __get_github_auth_token(package_name):
    token_name = package_name.upper()
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
                         f'please set one of the following environmental variables: {search_env}')

    return token
