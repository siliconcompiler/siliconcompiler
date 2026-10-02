import os
import pytest
import responses
import tarfile

from io import BytesIO

from siliconcompiler import Project
from siliconcompiler.package import Resolver
from siliconcompiler.package.cache import DataSourceUnavailableError
from siliconcompiler.package.gitlab import GitlabResolver, get_resolver

_API = "https://gitlab.com/api/v4/projects/g%2Fp"
_SHA = "9ed43f659b4803fd79b10de6d3c7d7aa4645c39f"


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    """Clears every variable a resolver named ``test`` could take a token from."""
    for prefix in ("GITLAB", "GL", "GIT", "GITHUB", "GH", "HTTPS", "HTTP"):
        monkeypatch.delenv(f"{prefix}_TOKEN", raising=False)
        monkeypatch.delenv(f"{prefix}_TEST_TOKEN", raising=False)


@pytest.fixture
def gitlab():
    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock:
        yield mock


def _tarball(members):
    """A gzip tarball holding one byte at each path in ``members``."""
    buffer = BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for member in members:
            info = tarfile.TarInfo(name=member)
            info.size = 1
            tar.addfile(info, BytesIO(b"x"))
    return buffer.getvalue()


def _release(*links, tag="v1.0", upcoming=False):
    return {"tag_name": tag, "upcoming_release": upcoming,
            "assets": {"links": list(links)}}


def _link(name, host="gitlab.com", direct=True):
    link = {"name": name, "url": f"https://{host}/files/{name}"}
    if direct:
        link["direct_asset_url"] = f"https://gitlab.com/g/p/-/releases/v1.0/downloads/{name}"
    return link


def _resolver(source):
    project = Project("testproj")
    project.option.set_cachedir(".")
    return Resolver.find_resolver(source)("test", project, source, "v1.0")


def _authorizations(mock):
    """``(url without query, Authorization header)`` for every request made."""
    return [(call.request.url.split("?")[0], call.request.headers.get("Authorization"))
            for call in mock.calls]


def test_get_resolver():
    assert get_resolver() == {"gitlab": GitlabResolver, "gitlab+private": GitlabResolver}


@pytest.mark.parametrize("source", ["gitlab://gitlab.com/g/p/v1.0/a.tar.gz",
                                    "gitlab+private://gitlab.com/g/p/v1.0/a.tar.gz"])
def test_find_resolver(source):
    assert Resolver.find_resolver(source) is GitlabResolver


@pytest.mark.parametrize("source,expect", [
    ("gitlab://gitlab.com/g/p/v1.0/a.tar.gz", ("gitlab.com", "g/p", "v1.0", "a.tar.gz")),
    ("gitlab://gitlab.com/g/s/p/v1.0/a.tar.gz", ("gitlab.com", "g/s/p", "v1.0", "a.tar.gz")),
    ("gitlab://gitlab.com/g/s/t/p/v1.0/a.tar.gz", ("gitlab.com", "g/s/t/p", "v1.0", "a.tar.gz")),
    ("gitlab://git.example.com:8443/g/p/v1.0/a.tar.gz",
     ("git.example.com:8443", "g/p", "v1.0", "a.tar.gz")),
    ("gitlab://gitlab.com/g/p//a.tar.gz", ("gitlab.com", "g/p", "", "a.tar.gz")),
])
def test_gitlab_path(source, expect):
    assert GitlabResolver("test", None, source, "v1.0").gitlab_path == expect


@pytest.mark.parametrize("source", [
    "gitlab://gitlab.com/p/v1.0/a.tar.gz",
    "gitlab://gitlab.com/g/p/v1.0/",
    "gitlab://gitlab.com/g//p/v1.0/a.tar.gz",
    "gitlab:///g/p/v1.0/a.tar.gz",
])
def test_improper_form(source):
    with pytest.raises(ValueError, match="is not in the proper form"):
        GitlabResolver("test", None, source, "v1.0")


@pytest.mark.parametrize("source", ["gitlab://SECRET@gitlab.com/g/p/v1.0/a.tar.gz",
                                    "gitlab://user:SECRET@gitlab.com/g/p/v1.0/a.tar.gz"])
def test_credential_in_url_refused(source):
    with pytest.raises(ValueError, match="carries a credential") as error:
        GitlabResolver("test", None, source, "v1.0")
    assert "SECRET" not in str(error.value)


@pytest.mark.parametrize("fmt", ["tar.gz", "tar.bz2", "zip"])
def test_source_archive_url(gitlab, fmt):
    gitlab.add(responses.GET, _API, json={})
    resolver = _resolver(f"gitlab://gitlab.com/g/p/v1.0/v1.0.{fmt}")
    assert resolver.download_url == f"{_API}/repository/archive.{fmt}?sha=v1.0"


def test_tag_with_slash(gitlab):
    """Written '%2F' in the URL, decoded to match, and encoded again for the API."""
    gitlab.add(responses.GET, _API, json={})
    resolver = _resolver("gitlab://gitlab.com/g/p/rel%2F1/rel%2F1.tar.gz")
    assert resolver.gitlab_path[2:] == ("rel/1", "rel/1.tar.gz")
    assert resolver.download_url.endswith("?sha=rel%2F1")


def test_release_lookup_quotes_tag(gitlab):
    gitlab.add(responses.GET, _API, json={})
    gitlab.add(responses.GET, f"{_API}/releases/rel%2F1",
               json=_release(_link("asset.tar.gz"), tag="rel/1"))
    resolver = _resolver("gitlab://gitlab.com/g/p/rel%2F1/asset.tar.gz")
    assert resolver.download_url.endswith("/downloads/asset.tar.gz")


def test_source_archive_is_flattened(gitlab):
    """The API names the top directory '<project>-<tag>-<commit>', taken as found."""
    gitlab.add(responses.GET, _API, json={})
    gitlab.add(responses.GET, f"{_API}/repository/archive.tar.gz",
               body=_tarball([f"p-v1.0-{_SHA}/f"]))
    resolver = _resolver("gitlab://gitlab.com/g/p/v1.0/v1.0.tar.gz")
    resolver.resolve_remote()
    assert os.listdir(resolver.cache_path) == ["f"]


def test_source_archive_not_flattened_when_not_alone(gitlab):
    gitlab.add(responses.GET, _API, json={})
    gitlab.add(responses.GET, f"{_API}/repository/archive.tar.gz",
               body=_tarball([f"p-v1.0-{_SHA}/f", "g"]))
    resolver = _resolver("gitlab://gitlab.com/g/p/v1.0/v1.0.tar.gz")
    resolver.resolve_remote()
    assert sorted(os.listdir(resolver.cache_path)) == ["g", f"p-v1.0-{_SHA}"]


def test_release_link(gitlab):
    gitlab.add(responses.GET, _API, json={})
    gitlab.add(responses.GET, f"{_API}/releases/v1.0",
               json=_release(_link("other.tar.gz"), _link("asset.tar.gz")))
    resolver = _resolver("gitlab://gitlab.com/g/p/v1.0/asset.tar.gz")
    assert resolver.download_url == \
        "https://gitlab.com/g/p/-/releases/v1.0/downloads/asset.tar.gz"


def test_release_link_without_direct_url(gitlab):
    """An instance too old for direct_asset_url leaves the link's own URL."""
    gitlab.add(responses.GET, _API, json={})
    gitlab.add(responses.GET, f"{_API}/releases/v1.0",
               json=_release(_link("asset.tar.gz", host="cdn.example.com", direct=False)))
    resolver = _resolver("gitlab://gitlab.com/g/p/v1.0/asset.tar.gz")
    assert resolver.download_url == "https://cdn.example.com/files/asset.tar.gz"


def test_release_link_is_not_flattened(gitlab):
    """A release asset is laid out however its author built it."""
    gitlab.add(responses.GET, _API, json={})
    gitlab.add(responses.GET, f"{_API}/releases/v1.0", json=_release(_link("asset.tar.gz")))
    gitlab.add(responses.GET, "https://gitlab.com/g/p/-/releases/v1.0/downloads/asset.tar.gz",
               body=_tarball(["pkg/f"]))
    resolver = _resolver("gitlab://gitlab.com/g/p/v1.0/asset.tar.gz")
    resolver.resolve_remote()
    assert os.listdir(resolver.cache_path) == ["pkg"]


def test_release_asset_missing(gitlab):
    gitlab.add(responses.GET, _API, json={})
    gitlab.add(responses.GET, f"{_API}/releases/v1.0", json=_release(_link("other.tar.gz")))
    resolver = _resolver("gitlab://gitlab.com/g/p/v1.0/asset.tar.gz")
    with pytest.raises(DataSourceUnavailableError, match="g/p/v1.0/asset.tar.gz"):
        resolver.download_url


@pytest.mark.parametrize("status,error", [(404, DataSourceUnavailableError),
                                          (500, FileNotFoundError)])
def test_release_lookup_failure(gitlab, status, error):
    gitlab.add(responses.GET, _API, json={})
    gitlab.add(responses.GET, f"{_API}/releases/v1.0", status=status)
    resolver = _resolver("gitlab://gitlab.com/g/p/v1.0/asset.tar.gz")
    with pytest.raises(error) as raised:
        resolver.download_url
    # A server error stays retryable.
    assert resolver.is_permanent_failure(raised.value) is (status == 404)


def test_latest_release(gitlab):
    gitlab.add(responses.GET, _API, json={})
    gitlab.add(responses.GET, f"{_API}/releases",
               json=[_release(tag="v3.0", upcoming=True), _release(tag="v2.0")])
    gitlab.add(responses.GET, f"{_API}/releases/v2.0",
               json=_release(_link("asset.tar.gz"), tag="v2.0"))
    resolver = _resolver("gitlab://gitlab.com/g/p//asset.tar.gz")
    assert resolver.download_url.endswith("/downloads/asset.tar.gz")


def test_latest_release_none(gitlab):
    gitlab.add(responses.GET, _API, json={})
    gitlab.add(responses.GET, f"{_API}/releases", json=[])
    resolver = _resolver("gitlab://gitlab.com/g/p//asset.tar.gz")
    with pytest.raises(DataSourceUnavailableError, match="has no release"):
        resolver.download_url


def _fetch_source_archive(gitlab, source, api, public):
    gitlab.add(responses.GET, api, json={}, status=200 if public else 404)
    gitlab.add(responses.GET, f"{api}/repository/archive.tar.gz", body=_tarball(["f"]))
    _resolver(source).resolve_remote()
    return _authorizations(gitlab)


def test_public_project_sends_no_token(gitlab, monkeypatch):
    """A stale token is refused even by a public project, so none is sent to one."""
    monkeypatch.setenv("GITLAB_TOKEN", "SECRET")
    sent = _fetch_source_archive(gitlab, "gitlab://gitlab.com/g/p/v1.0/v1.0.tar.gz", _API,
                                 public=True)
    assert [auth for _, auth in sent] == [None, None]


@pytest.mark.parametrize("var", ["GITLAB_TOKEN", "GITLAB_TEST_TOKEN", "GL_TOKEN", "GIT_TOKEN"])
def test_private_project_on_gitlab_com(gitlab, monkeypatch, var):
    monkeypatch.setenv(var, "SECRET")
    sent = _fetch_source_archive(gitlab, "gitlab://gitlab.com/g/p/v1.0/v1.0.tar.gz", _API,
                                 public=False)
    assert sent == [(_API, None),
                    (f"{_API}/repository/archive.tar.gz", "Bearer SECRET")]


def test_gitlab_token_preferred_over_git_token(gitlab, monkeypatch):
    monkeypatch.setenv("GITLAB_TOKEN", "SECRET_GL")
    monkeypatch.setenv("GIT_TOKEN", "SECRET_GIT")
    sent = _fetch_source_archive(gitlab, "gitlab://gitlab.com/g/p/v1.0/v1.0.tar.gz", _API,
                                 public=False)
    assert sent[-1][1] == "Bearer SECRET_GL"


@pytest.mark.parametrize("host", ["gitlab.example.com", "gitlab.attacker.example"])
def test_self_hosted_never_gets_gitlab_token(gitlab, monkeypatch, host):
    """A host that calls itself GitLab is not shown to be GitLab's."""
    monkeypatch.setenv("GITLAB_TOKEN", "SECRET_GL")
    monkeypatch.setenv("GL_TOKEN", "SECRET_GL")
    api = f"https://{host}/api/v4/projects/g%2Fp"
    sent = _fetch_source_archive(gitlab, f"gitlab://{host}/g/p/v1.0/v1.0.tar.gz", api,
                                 public=False)
    assert [auth for _, auth in sent] == [None, None]


def test_self_hosted_gets_git_token(gitlab, monkeypatch):
    monkeypatch.setenv("GITLAB_TOKEN", "SECRET_GL")
    monkeypatch.setenv("GIT_TOKEN", "SECRET_GIT")
    api = "https://gitlab.example.com/api/v4/projects/g%2Fp"
    sent = _fetch_source_archive(gitlab, "gitlab://gitlab.example.com/g/p/v1.0/v1.0.tar.gz",
                                 api, public=False)
    assert sent[-1][1] == "Bearer SECRET_GIT"


def test_private_scheme_skips_anonymous_attempt(gitlab, monkeypatch):
    monkeypatch.setenv("GITLAB_TOKEN", "SECRET")
    gitlab.add(responses.GET, f"{_API}/releases/v1.0", json=_release(_link("asset.tar.gz")))
    gitlab.add(responses.GET, "https://gitlab.com/g/p/-/releases/v1.0/downloads/asset.tar.gz",
               body=_tarball(["f"]))
    resolver = _resolver("gitlab+private://gitlab.com/g/p/v1.0/asset.tar.gz")
    resolver.resolve_remote()
    assert _authorizations(gitlab) == [
        (f"{_API}/releases/v1.0", "Bearer SECRET"),
        ("https://gitlab.com/g/p/-/releases/v1.0/downloads/asset.tar.gz", "Bearer SECRET"),
    ]


def test_no_token_to_link_on_another_host(gitlab, monkeypatch):
    """A release link can point anywhere; its host is not GitLab's to vouch for."""
    monkeypatch.setenv("GITLAB_TOKEN", "SECRET")
    gitlab.add(responses.GET, f"{_API}/releases/v1.0",
               json=_release(_link("asset.tar.gz", host="cdn.example.com", direct=False)))
    gitlab.add(responses.GET, "https://cdn.example.com/files/asset.tar.gz", body=_tarball(["f"]))
    resolver = _resolver("gitlab+private://gitlab.com/g/p/v1.0/asset.tar.gz")
    resolver.resolve_remote()
    assert _authorizations(gitlab) == [
        (f"{_API}/releases/v1.0", "Bearer SECRET"),
        ("https://cdn.example.com/files/asset.tar.gz", None),
    ]
