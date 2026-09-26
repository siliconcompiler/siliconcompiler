import io
import os
import tarfile

import pytest

from siliconcompiler import Project
from siliconcompiler.package import FetchPolicy, FetchRefused, current_fetch_policy, \
    fetch_policy
from siliconcompiler.package.git import GitResolver, _lfs_endpoint, _submodule_url
from siliconcompiler.package.https import HTTPResolver


# Resolving somebody else's sources: nothing of this process's is sent, and
# every URL is checked before it is contacted.


def policy(tmp_path, checked, **extra):
    def check(url):
        checked.append(url)
        if "evil" in url:
            raise FetchRefused(f"{url} is refused")
    return FetchPolicy(check_url=check, home=str(tmp_path / "home"), **extra)


def project(tmp_path):
    proj = Project("fetched")
    proj.option.set_cachedir(str(tmp_path / "cache"))
    return proj


def test_the_policy_is_per_thread_and_nests(tmp_path):
    outer = policy(tmp_path, [])
    inner = policy(tmp_path, [])

    assert current_fetch_policy() is None
    with fetch_policy(outer):
        with fetch_policy(inner):
            assert current_fetch_policy() is inner
        assert current_fetch_policy() is outer
    assert current_fetch_policy() is None


def test_no_token_is_read_under_a_policy(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "the-servers-own")
    resolver = HTTPResolver("fetched", project(tmp_path),
                            "https://github.com/org/repo/archive/refs/tags/", "v1")

    assert resolver._get_auth_token(["GITHUB"]) == "the-servers-own"
    with fetch_policy(policy(tmp_path, [])):
        with pytest.raises(ValueError, match="no credential"):
            resolver._get_auth_token(["GITHUB"])


###########################
# https
###########################

class Response:
    def __init__(self, status, body=b"", location=None):
        self.status_code, self.ok = status, status < 400
        self.headers = {"Location": location} if location else {}
        self.content = body

    def iter_content(self, size):
        yield self.content

    def close(self):
        pass


class Session:
    def __init__(self, answers):
        self.answers, self.sent, self.trust_env = answers, [], True

    def get(self, url, **kwargs):
        assert kwargs["allow_redirects"] is False
        self.sent.append((url, self.trust_env, dict(kwargs.get("headers") or {})))
        return self.answers[url]


def tarball():
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        info = tarfile.TarInfo("data.txt")
        info.size = 4
        tar.addfile(info, io.BytesIO(b"data"))
    return buffer.getvalue()


@pytest.fixture
def through(monkeypatch):
    from siliconcompiler.package import https

    def use(session):
        monkeypatch.setattr(https.requests, "Session", lambda: session)
        return session
    return use


def test_every_hop_is_checked_and_nothing_of_ours_is_sent(tmp_path, through, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "the-servers-own")
    first, second = "https://example.com/a.tar.gz", "https://cdn.example.com/a.tar.gz"
    session = through(Session({first: Response(302, location=second),
                               second: Response(200, tarball())}))
    checked = []
    resolver = HTTPResolver("fetched", project(tmp_path), first, "v1")

    with fetch_policy(policy(tmp_path, checked)):
        path = resolver.resolve()

    assert checked == [first, second]
    assert [(url, trust) for url, trust, _ in session.sent] == [(first, False), (second, False)]
    assert not any("Authorization" in headers for _, _, headers in session.sent)
    assert open(os.path.join(path, "data.txt")).read() == "data"


def test_a_hop_the_policy_refuses_is_never_contacted(tmp_path, through):
    first = "https://example.com/a.tar.gz"
    session = through(Session({first: Response(302, location="https://evil.example/a")}))

    with fetch_policy(policy(tmp_path, [])):
        with pytest.raises(FetchRefused):
            HTTPResolver("fetched", project(tmp_path), first, "v1").resolve()

    assert [url for url, _, _ in session.sent] == [first]


def test_a_download_past_the_ceiling_is_refused(tmp_path, through):
    url = "https://example.com/a.tar.gz"
    through(Session({url: Response(200, tarball())}))

    with fetch_policy(policy(tmp_path, [], max_bytes=10)):
        with pytest.raises(FetchRefused, match="larger than"):
            HTTPResolver("fetched", project(tmp_path), url, "v1").resolve()


def test_a_url_carrying_a_credential_is_refused(tmp_path, through):
    through(Session({}))

    with fetch_policy(policy(tmp_path, [])):
        with pytest.raises(FetchRefused, match="credential"):
            HTTPResolver("fetched", project(tmp_path),
                         "https://user:secret@example.com/a.tar.gz", "v1").resolve()


###########################
# git
###########################

@pytest.mark.parametrize("source", ["git+ssh://git@github.com/org/repo.git",
                                    "git://github.com/org/repo.git",
                                    "git+https://user:secret@github.com/org/repo.git"])
def test_only_a_plain_https_repository_is_cloned(tmp_path, source, monkeypatch):
    import git

    cloned = []
    monkeypatch.setattr(git.Repo, "clone_from", lambda *args, **kwargs: cloned.append(args))

    with fetch_policy(policy(tmp_path, [])):
        with pytest.raises(FetchRefused):
            GitResolver("fetched", project(tmp_path), source, "v1").resolve_remote()

    assert cloned == []


def test_a_clone_is_checked_first_and_runs_isolated(tmp_path, monkeypatch):
    import git

    seen = {}

    def clone(url, path, env=None, **kwargs):
        seen.update(url=url, env=env)
        raise git.GitCommandError("clone", 128, "stop here")

    monkeypatch.setattr(git.Repo, "clone_from", clone)
    checked = []
    source = "git+https://github.com/org/repo.git"

    with fetch_policy(policy(tmp_path, checked, proxy="http://127.0.0.1:9")):
        with pytest.raises(git.GitCommandError):
            GitResolver("fetched", project(tmp_path), source, "v1").resolve_remote()

    assert checked == ["https://github.com/org/repo.git"] == [seen["url"]]
    env = seen["env"]
    settings = {env[f"GIT_CONFIG_KEY_{n}"]: env[f"GIT_CONFIG_VALUE_{n}"]
                for n in range(int(env["GIT_CONFIG_COUNT"]))}
    assert settings["protocol.allow"] == "never"
    assert settings["protocol.https.allow"] == "always"
    assert settings["http.followRedirects"] == "false"
    assert settings["credential.helper"] == ""
    assert settings["http.proxy"] == "http://127.0.0.1:9"
    assert env["HOME"] == str(tmp_path / "home")
    assert env["GIT_CONFIG_GLOBAL"] == os.devnull and env["SSH_AUTH_SOCK"] == ""
    assert env["HTTPS_PROXY"] == "http://127.0.0.1:9"


def test_a_submodule_off_the_policy_stops_before_git_fetches_it(tmp_path):
    class Submodule:
        path, url = "ip", "https://evil.example/ip.git"

    class Git:
        def __init__(self):
            self.calls = []

        def submodule(self, *args, **kwargs):
            self.calls.append(args)

    class Repo:
        working_dir = str(tmp_path)
        submodules = [Submodule()]
        git = Git()

    (tmp_path / ".gitmodules").write_text("[submodule]\n")
    resolver = GitResolver("fetched", project(tmp_path),
                           "git+https://github.com/org/repo.git", "v1")

    with pytest.raises(FetchRefused):
        resolver._submodules_under_policy(policy(tmp_path, []), Repo(),
                                          "https://github.com/org/repo.git", {}, {}, 0)
    assert Repo.git.calls == []


@pytest.mark.parametrize("url,expected", [
    ("../other.git", "https://github.com/org/other.git"),
    ("./nested.git", "https://github.com/org/repo.git/nested.git"),
    ("https://gitlab.com/x/y.git", "https://gitlab.com/x/y.git"),
])
def test_a_relative_submodule_url_reads_as_git_reads_it(url, expected):
    assert _submodule_url("https://github.com/org/repo.git", url) == expected


def test_the_lfs_endpoint_is_git_lfs_default():
    assert _lfs_endpoint("https://github.com/org/repo.git") == \
        "https://github.com/org/repo.git/info/lfs"
    assert _lfs_endpoint("https://github.com/org/repo") == \
        "https://github.com/org/repo.git/info/lfs"
