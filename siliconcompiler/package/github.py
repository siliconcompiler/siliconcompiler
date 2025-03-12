import os
from github import Github, Auth
from github.GithubException import UnknownObjectException
from urllib.parse import urlparse
from siliconcompiler.package.https import http_resolver


def get_resolver(url):
    if url.scheme in ("github",):
        return github_any_resolver
    if url.scheme in ("github+private",):
        return github_private_resolver
    return None


def github_any_resolver(chip, package, path, ref, url, fetch):
    if not fetch:
        return http_resolver(chip, package, path, ref, url, fetch)

    try:
        return __github_resolver(chip, package, path, ref, url)
    except UnknownObjectException:
        return github_private_resolver(chip, package, path, ref, url, fetch)


def github_private_resolver(chip, package, path, ref, url, fetch):
    if not fetch:
        return http_resolver(chip, package, path, ref, url, fetch)

    gh = Github(auth=Auth.Token(__get_github_auth_token(package)))

    return __github_resolver(chip, package, path, ref, url, gh=gh)


def __github_resolver(chip, package, path, ref, url, gh=None):
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

    return http_resolver(chip, package, release_url, ref, urlparse(release_url), True)


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
