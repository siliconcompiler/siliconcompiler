import base64
import logging
import pytest
import re
import shutil
import subprocess
import sys
import threading

import os.path

from git import Repo, Actor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch, MagicMock
from urllib.parse import urlparse

from siliconcompiler.package.git import GitAuthenticationError, GitResolver
from siliconcompiler import Project


# Any of these leaking in from the developer's own shell would change the URL
# git_path builds and silently rewrite what these tests are asserting.
_TOKEN_ENV = re.compile(r'^(GITHUB|GH|GITLAB|GL|BITBUCKET|GIT)_([A-Z0-9]+_)?TOKEN$')


@pytest.fixture(autouse=True)
def clean_token_env(monkeypatch):
    """Removes every token variable the resolver searches, ambient or otherwise."""
    for name in list(os.environ):
        if _TOKEN_ENV.match(name):
            monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def mock_git(monkeypatch):
    class MockGit:
        @staticmethod
        def checkout(*args, **kwargs):
            pass

        @staticmethod
        def update_environment(*args, **kwargs):
            pass

    def clone(url, to_path, **kwargs):
        Path(to_path).mkdir(parents=True, exist_ok=True)
        repo = Repo.init(to_path)

        test_path = Path(to_path) / 'pyproject.toml'
        test_path.touch()

        author = Actor("author", "author@example.com")
        committer = Actor("committer", "committer@example.com")
        repo.index.add('pyproject.toml')
        repo.index.commit('msg', author=author, committer=committer)

        repo.git = MockGit

        return repo

    monkeypatch.setattr("git.Repo.clone_from", clone)


@pytest.mark.parametrize('path,ref,cache_id', [
    ('git+https://github.com/siliconcompiler/siliconcompiler',
     'main',
     '933ab1d5daa72905'),
    ('git://github.com/siliconcompiler/siliconcompiler',
     'main',
     '4bd21abf91c854d6'),
])
def test_dependency_path_download_git(path, ref, cache_id, tmp_path):
    proj = Project("testproj")
    proj.set("option", "cachedir", tmp_path)

    resolver = GitResolver("testgit", proj, path, ref)
    cache_dir = os.path.join(tmp_path, "dataroot", f"testgit-{ref}-{cache_id}")
    assert resolver.resolve() == Path(cache_dir)
    assert os.path.isfile(os.path.join(cache_dir, "pyproject.toml"))


def test_git_path_git_ssh():
    resolver = GitResolver("testgit", Project(),
                           "git+ssh://github.com/test_owner/test_repo", "main")
    assert resolver.git_path == "ssh://github.com/test_owner/test_repo"


def test_git_path_ssh():
    resolver = GitResolver("testgit", Project(),
                           "ssh://github.com/test_owner/test_repo", "main")
    assert resolver.git_path == "ssh://github.com/test_owner/test_repo"


def test_git_path_default():
    resolver = GitResolver("testgit", Project(),
                           "git://github.com/test_owner/test_repo", "main")
    assert resolver.git_path == "https://github.com/test_owner/test_repo"


@pytest.mark.skipif(sys.platform == "win32", reason="Appears to cause issues on windows machines")
def test_dirty_warning(project_logger, caplog, tmp_path):
    proj = Project("testproj")
    project_logger(proj)
    proj.logger.setLevel(logging.INFO)

    assert Path(tmp_path).exists()

    resolver = GitResolver("testgit", proj, "git+ssh://github.com/test_owner/test_repo", "main")
    resolver.resolve()

    assert Path(resolver.cache_path).exists()

    # Make cache writable to simulate a dirty repository (it's now read-only by default)
    resolver._make_writable(resolver.cache_path)

    file = Path(resolver.cache_path).joinpath('file.txt')
    file.touch()

    resolver.resolve()

    assert "The repo of the cached data is dirty." in caplog.text


# ============================================================================
# Additional GitResolver Tests
# ============================================================================

def test_git_resolver_get_resolver():
    """Test get_resolver returns correct mapping for Git schemes."""
    from siliconcompiler.package.git import get_resolver
    resolvers = get_resolver()
    assert isinstance(resolvers, dict)
    assert "git" in resolvers
    assert "git+https" in resolvers
    assert "git+ssh" in resolvers
    assert "ssh" in resolvers
    for resolver in resolvers.values():
        assert resolver is GitResolver


def test_git_resolver_check_cache_no_path():
    """Test check_cache returns False when path doesn't exist."""
    resolver = GitResolver("test", None, "git://github.com/owner/repo.git", "main")
    with patch("os.path.exists", return_value=False):
        assert resolver.check_cache() is False


def test_git_resolver_check_cache_valid_repo(monkeypatch):
    """Test check_cache returns True for valid repository."""
    resolver = GitResolver("test", None, "git://github.com/owner/repo.git", "main")

    mock_repo = MagicMock()
    mock_repo.untracked_files = []
    mock_repo.index.diff.return_value = []

    import siliconcompiler.package.git as git_module
    with patch("os.path.exists", return_value=True), \
         patch.object(git_module, "Repo", return_value=mock_repo):
        assert resolver.check_cache() is True


def test_git_resolver_check_cache_dirty_repo(monkeypatch, caplog):
    """Test check_cache warns about dirty repository."""
    resolver = GitResolver("test", Project("testproj"), "git://github.com/owner/repo.git", "main")

    mock_repo = MagicMock()
    mock_repo.untracked_files = ["untracked.txt"]
    mock_repo.index.diff.return_value = []

    import siliconcompiler.package.git as git_module
    with patch("os.path.exists", return_value=True), \
         patch.object(git_module, "Repo", return_value=mock_repo):
        caplog.clear()
        caplog.set_level(logging.WARNING)
        result = resolver.check_cache()
        assert result is True
        # Logger warning is in the resolver
        assert resolver.logger is not None


def test_git_resolver_check_cache_corrupted_repo(monkeypatch, caplog):
    """Test check_cache removes corrupted repository."""
    resolver = GitResolver("test", Project("testproj"), "git://github.com/owner/repo.git", "main")

    import siliconcompiler.package.git as git_module
    from git.exc import GitCommandError

    with patch("os.path.exists", return_value=True), \
         patch.object(git_module, "Repo",
                      side_effect=GitCommandError("git", "init", stderr=b"corrupted")), \
         patch.object(git_module, "shutil") as mock_shutil:
        result = resolver.check_cache()
        assert result is False
        mock_shutil.rmtree.assert_called_once()


def test_git_resolver_git_path_ssh():
    """Test git_path constructs SSH URL correctly."""
    resolver = GitResolver("test", None, "git+ssh://git@github.com/owner/repo.git", "main")
    assert resolver.git_path == "ssh://git@github.com/owner/repo.git"


def test_git_resolver_git_path_ssh_ignores_token(monkeypatch):
    """A token never rewrites an SSH URL; SSH authenticates with keys."""
    monkeypatch.setenv("GITHUB_TOKEN", "test_token")

    resolver = GitResolver("test", None, "git+ssh://git@github.com/owner/repo.git", "main")
    assert resolver.git_path == "ssh://git@github.com/owner/repo.git"


def test_git_resolver_git_path_https_no_token():
    """Test git_path constructs HTTPS URL without token."""
    resolver = GitResolver("test", None, "git+https://github.com/owner/repo.git", "main")
    assert resolver.git_path == "https://github.com/owner/repo.git"


@pytest.mark.parametrize("env,source,expect", [
    # The token is the basic-auth password under the username each host expects.
    # A bare token in the username field with no password is accepted by GitHub
    # for classic PATs but not for App installation tokens, and by GitLab for
    # neither, so the username is never left for the server to infer.
    ("GITHUB_TOKEN", "git+https://github.com/owner/repo.git",
     "https://x-access-token:tok@github.com/owner/repo.git"),
    ("GITLAB_TOKEN", "git+https://gitlab.com/owner/repo.git",
     "https://oauth2:tok@gitlab.com/owner/repo.git"),
    ("BITBUCKET_TOKEN", "git+https://bitbucket.org/owner/repo.git",
     "https://x-token-auth:tok@bitbucket.org/owner/repo.git"),
    # A self-hosted instance still gets the right username, but its credential
    # comes from the generic GIT_TOKEN: a forge name in a label is not evidence
    # that the forge owns the host, so it cannot unlock that forge's variable.
    ("GIT_TOKEN", "git+https://github.mycorp.com/owner/repo.git",
     "https://x-access-token:tok@github.mycorp.com/owner/repo.git"),
    ("GIT_TOKEN", "git+https://gitlab.example.com/owner/repo.git",
     "https://oauth2:tok@gitlab.example.com/owner/repo.git"),
    # An unrecognised host keeps the token in the username field, where it has
    # always gone, but with the empty password spelled out. Identical on the
    # wire; the difference is that git no longer falls through to a prompt.
    ("GIT_TOKEN", "git+https://git.example.com/owner/repo.git",
     "https://tok:@git.example.com/owner/repo.git"),
    # ...and a host that merely contains 'github' is not GitHub.
    ("GIT_TOKEN", "git+https://mygithub.internal/owner/repo.git",
     "https://tok:@mygithub.internal/owner/repo.git"),
    # The git:// scheme is normalised to https and takes a token too.
    ("GITHUB_TOKEN", "git://github.com/owner/repo.git",
     "https://x-access-token:tok@github.com/owner/repo.git"),
])
def test_git_path_token_username_per_host(monkeypatch, env, source, expect):
    """Each forge gets the basic-auth username it expects."""
    monkeypatch.setenv(env, "tok")

    resolver = GitResolver("test", None, source, "main")
    assert resolver.git_path == expect


def test_git_path_preserves_port(monkeypatch):
    """The port survives token injection; url.hostname would have dropped it."""
    monkeypatch.setenv("GIT_TOKEN", "tok")

    resolver = GitResolver("test", None, "git+https://gitlab.example.com:8443/o/r.git", "main")
    assert resolver.git_path == "https://oauth2:tok@gitlab.example.com:8443/o/r.git"


def test_git_path_preserves_ipv6_host(monkeypatch):
    """Bracketed IPv6 literals survive; url.hostname would have unwrapped them."""
    monkeypatch.setenv("GIT_TOKEN", "tok")

    resolver = GitResolver("test", None, "git+https://[::1]:8443/o/r.git", "main")
    assert resolver.git_path == "https://tok:@[::1]:8443/o/r.git"


def test_git_path_url_username_wins(monkeypatch):
    """A username in the URL is the escape hatch for a host we do not know."""
    monkeypatch.setenv("GIT_TOKEN", "tok")

    resolver = GitResolver("test", None, "git+https://oauth2@git.example.com/o/r.git", "main")
    assert resolver.git_path == "https://oauth2:tok@git.example.com/o/r.git"


@pytest.mark.parametrize("source", [
    "git+https://user:pass@git.example.com/o/r.git",
    # An explicitly empty password is still a password the user chose.
    "git+https://user:@git.example.com/o/r.git",
])
def test_git_path_url_password_untouched(monkeypatch, source):
    """A credential already in the URL is left exactly as written."""
    monkeypatch.setenv("GIT_TOKEN", "tok")

    resolver = GitResolver("test", None, source, "main")
    assert resolver.git_path == source.replace("git+https://", "https://")


def test_git_path_quotes_token(monkeypatch):
    """A token carrying URL delimiters is encoded rather than corrupting the netloc."""
    monkeypatch.setenv("GIT_TOKEN", "a/b@c:d")

    resolver = GitResolver("test", None, "git+https://git.example.com/o/r.git", "main")
    assert resolver.git_path == "https://a%2Fb%40c%3Ad:@git.example.com/o/r.git"


@pytest.mark.parametrize("env,source", [
    ("GITHUB_TOKEN", "git+https://github.attacker.example/o/r.git"),
    ("GITLAB_TOKEN", "git+https://gitlab.attacker.example/o/r.git"),
    ("BITBUCKET_TOKEN", "git+https://bitbucket.attacker.example/o/r.git"),
    # A forge name glued to a longer label is not that forge either.
    ("GITHUB_TOKEN", "git+https://notgithub.com/o/r.git"),
    ("GITHUB_TOKEN", "git+https://github.com.attacker.example/o/r.git"),
])
def test_forge_token_not_sent_to_lookalike_host(monkeypatch, env, source):
    """
    A forge's own token is never handed to a host that forge does not own.

    A forge name in some DNS label says nothing about who controls the host, so
    it cannot be what unlocks the ambient GITHUB_TOKEN/GITLAB_TOKEN. Without a
    GIT_TOKEN these URLs must carry no credential at all.
    """
    monkeypatch.setenv(env, "secret")

    resolver = GitResolver("test", None, source, "main")
    assert "secret" not in resolver.git_path
    assert resolver.git_path == source.replace("git+https://", "https://")


@pytest.mark.parametrize("hostname,expect", [
    ("github.com", "github"),
    ("gist.github.com", "github"),
    ("gitlab.com", "gitlab"),
    ("bitbucket.org", "bitbucket"),
    # Ownership, not name matching: none of these belong to the forge.
    ("github.attacker.example", None),
    ("gitlab.attacker.example", None),
    ("github.com.attacker.example", None),
    ("notgithub.com", None),
    ("github.mycorp.com", None),
    ("gitlab.example.com", None),
    (None, None),
])
def test_saas_forge(hostname, expect):
    """Only a forge's own domains unlock that forge's token variables."""
    assert GitResolver._saas_forge(hostname) == expect


def test_git_path_percent_encoded_username(monkeypatch):
    """
    A percent-escaped username round-trips instead of being double-encoded.

    ParseResult.username hands back the raw escapes, so re-quoting without
    decoding first would turn 'user%40corp' into 'user%2540corp' and
    authenticate as the wrong name.
    """
    monkeypatch.setenv("GIT_TOKEN", "tok")

    resolver = GitResolver("test", None,
                           "git+https://user%40corp@git.example.com/o/r.git", "main")
    assert resolver.git_path == "https://user%40corp:tok@git.example.com/o/r.git"


def test_git_path_github_token_not_sent_to_gitlab(monkeypatch):
    """GITHUB_TOKEN is scoped to GitHub hosts and is not leaked elsewhere."""
    monkeypatch.setenv("GITHUB_TOKEN", "ghtok")

    resolver = GitResolver("test", None, "git+https://gitlab.com/o/r.git", "main")
    assert resolver.git_path == "https://gitlab.com/o/r.git"


@pytest.mark.parametrize("env,expect", [
    ("GITHUB_TEST_TOKEN", "x-access-token:package"),
    ("GITHUB_TOKEN", "x-access-token:package"),
    ("GH_TOKEN", "x-access-token:package"),
    ("GIT_TOKEN", "x-access-token:package"),
])
def test_git_path_github_token_env_names(monkeypatch, env, expect):
    """Every GitHub token variable, package-specific or not, is still honoured."""
    monkeypatch.setenv(env, "package")

    resolver = GitResolver("test", None, "git+https://github.com/o/r.git", "main")
    assert resolver.git_path == f"https://{expect}@github.com/o/r.git"


@pytest.mark.parametrize("env", ["GITLAB_TEST_TOKEN", "GITLAB_TOKEN", "GL_TOKEN", "GIT_TOKEN"])
def test_git_path_gitlab_token_env_names(monkeypatch, env):
    """GITLAB_TOKEN and friends reach a GitLab host; previously only GIT_TOKEN did."""
    monkeypatch.setenv(env, "tok")

    resolver = GitResolver("test", None, "git+https://gitlab.com/o/r.git", "main")
    assert resolver.git_path == "https://oauth2:tok@gitlab.com/o/r.git"


def test_git_path_token_precedence(monkeypatch):
    """The package-specific variable outranks the general one."""
    monkeypatch.setenv("GITHUB_TEST_TOKEN", "specific")
    monkeypatch.setenv("GITHUB_TOKEN", "general")
    monkeypatch.setenv("GIT_TOKEN", "fallback")

    resolver = GitResolver("test", None, "git+https://github.com/o/r.git", "main")
    assert resolver.git_path == "https://x-access-token:specific@github.com/o/r.git"


@pytest.mark.parametrize("hostname,expect", [
    ("github.com", "github"),
    ("GitHub.COM", "github"),
    ("api.github.com", "github"),
    ("github.mycorp.com", "github"),
    ("gitlab.com", "gitlab"),
    ("gitlab.example.com", "gitlab"),
    ("bitbucket.org", "bitbucket"),
    ("mygithub.internal", None),
    ("githubusercontent.com", None),
    ("git.example.com", None),
    ("", None),
    (None, None),
])
def test_host_forge(hostname, expect):
    """Forge detection matches whole labels, case-insensitively."""
    assert GitResolver._host_forge(hostname) == expect


@pytest.mark.parametrize("hostname,expect", [
    ("github.com", "x-access-token"),
    ("github.mycorp.com", "x-access-token"),
    ("gitlab.com", "oauth2"),
    ("gitlab.example.com", "oauth2"),
    ("bitbucket.org", "x-token-auth"),
    # No username for an unknown host: the caller falls back to putting the token
    # in the username field with an explicit empty password.
    ("git.example.com", None),
    ("mygithub.internal", None),
    (None, None),
])
def test_token_username(hostname, expect):
    """The basic-auth username is pinned per host, independently of URL building."""
    assert GitResolver._token_username(hostname) == expect


def test_git_path_hostless_url(monkeypatch):
    """A URL with no host does not raise; url.hostname is None there."""
    monkeypatch.setenv("GIT_TOKEN", "tok")

    resolver = GitResolver("test", None, "git+https:///owner/repo.git", "main")
    assert resolver.git_path == "https:///owner/repo.git"


def test_git_env_disables_prompt_without_tty():
    """
    Without a terminal neither prompting route can be answered, so both close.

    GIT_TERMINAL_PROMPT only closes the terminal one. An askpass helper left in
    the environment would still be called and would block on a dialog no build
    machine shows, so GIT_ASKPASS is emptied as well -- git then skips askpass
    entirely, including the core.askpass and SSH_ASKPASS fallbacks.
    """
    with patch.object(sys, "stdin", MagicMock(isatty=MagicMock(return_value=False))):
        assert GitResolver._git_env() == {"GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": ""}


def test_git_env_leaves_interactive_alone():
    """Interactively the prompt still works, so a developer is still asked."""
    with patch.object(sys, "stdin", MagicMock(isatty=MagicMock(return_value=True))):
        assert GitResolver._git_env() == {}


def test_git_env_handles_closed_stdin():
    """A closed stdin raises from isatty(); that is not a terminal either."""
    stdin = MagicMock()
    stdin.isatty.side_effect = ValueError("I/O operation on closed file")
    with patch.object(sys, "stdin", stdin):
        assert GitResolver._git_env() == {"GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": ""}


@pytest.mark.parametrize("url,expect", [
    ("https://x-access-token:ghs_SECRET@github.com/o/r.git",
     "https://x-access-token:***@github.com/o/r.git"),
    ("https://oauth2:SECRET@gitlab.com/o/r.git",
     "https://oauth2:***@gitlab.com/o/r.git"),
    ("https://x-token-auth:SECRET@bitbucket.org/o/r.git",
     "https://x-token-auth:***@bitbucket.org/o/r.git"),
    # Self-hosted keeps its public username too.
    ("https://oauth2:SECRET@gitlab.corp.com:8443/o/r.git",
     "https://oauth2:***@gitlab.corp.com:8443/o/r.git"),
    # Fallback form: the username IS the token, so it cannot be shown.
    ("https://SECRET:@git.example.com/o/r.git", "https://***@git.example.com/o/r.git"),
    ("https://SECRET:@[::1]:8443/o/r.git", "https://***@[::1]:8443/o/r.git"),
    # A username this resolver did not choose is not known to be public.
    ("https://myuser:SECRET@git.example.com/o/r.git",
     "https://***@git.example.com/o/r.git"),
    # Nothing to redact.
    ("https://github.com/o/r.git", "https://github.com/o/r.git"),
])
def test_redact_url(url, expect):
    """No credential reaches the log, whichever URL form carried it."""
    redacted = GitResolver._redact_url(url)
    assert redacted == expect
    assert "SECRET" not in redacted


def test_clone_logs_redacted_url_but_clones_with_the_real_one(monkeypatch, caplog):
    """The log is redacted while git still receives the working credential."""
    monkeypatch.setenv("GITHUB_TOKEN", "ghs_SECRET")
    proj = Project("testproj")
    resolver = GitResolver("test", proj, "git+https://github.com/owner/repo.git", "main")
    resolver.logger.setLevel(logging.INFO)

    mock_repo = MagicMock()
    mock_repo.submodules = []

    import siliconcompiler.package.git as git_module
    with patch.object(git_module, "Repo") as mock_repo_class, \
         patch.object(GitResolver, "_repo_uses_lfs", return_value=False):
        mock_repo_class.clone_from.return_value = mock_repo
        resolver.resolve_remote()

    assert "ghs_SECRET" not in caplog.text
    assert "x-access-token:***@github.com" in caplog.text
    # ...but the clone itself got the real credential.
    assert mock_repo_class.clone_from.call_args[0][0] == \
        "https://x-access-token:ghs_SECRET@github.com/owner/repo.git"


@pytest.mark.parametrize("error", [
    GitAuthenticationError("nope"),
    RuntimeError("connection reset"),
])
def test_auth_failure_is_not_permanent(error):
    """
    A credential failure must stay retryable.

    The failure cache is keyed by cache_id -- a hash of the source URI and
    reference -- which says nothing about credentials. Recording an auth failure
    as settled would outlive the expired token that caused it and keep refusing
    the source after a valid one is set. The HTTPS resolver takes the same
    position on 401 and 403.
    """
    resolver = GitResolver("test", None, "git+https://github.com/o/r.git", "main")
    assert resolver.is_permanent_failure(error) is False


@pytest.fixture
def auth_probe():
    """
    An HTTP server that refuses every request and records what it was sent.

    Asserting on the URL string cannot show what git actually transmits, and that
    is the whole of this defect: the old and new forms differ in one character
    and in whether git has a fallback left when the server says no.
    """
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            seen.append(self.headers.get("Authorization"))
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="git"')
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *args):
            pass

    # Threaded, with daemon threads: a handler left mid-request must never be
    # able to wedge shutdown and take the whole test with it.
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1], seen
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=10)


def _probe_git(port, userinfo):
    """Points git at the probe carrying ``userinfo``, and returns its stderr."""
    host = f"{userinfo}@127.0.0.1:{port}" if userinfo else f"127.0.0.1:{port}"

    # Built from nothing rather than inherited, because this asserts on the exact
    # bytes git transmits and the ambient environment can change them. Dropping
    # the inherited variables is also what stops the run hanging: GIT_TERMINAL_PROMPT
    # closes only the *terminal* prompt, so an askpass helper left in the
    # environment -- macOS sessions routinely have one -- would still be called
    # and would sit waiting on a GUI dialog that never appears.
    home = os.path.abspath("probe-home")
    os.makedirs(home, exist_ok=True)
    env = {
        # An empty HOME plus no system or global config keeps the developer's
        # credential helpers, proxies and insteadOf rewrites out of the result.
        "HOME": home,
        "USERPROFILE": home,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
    }
    # Carried over only because git needs them to run at all -- SYSTEMROOT for
    # sockets and TEMP/TMP for scratch files on Windows. None of them can change
    # which credential git offers.
    for passthrough in ("PATH", "SYSTEMROOT", "TEMP", "TMP"):
        if passthrough in os.environ:
            env[passthrough] = os.environ[passthrough]
    return subprocess.run(
        ["git", "-c", "credential.helper=", "ls-remote", f"http://{host}/repo.git"],
        capture_output=True, text=True, timeout=30, env=env).stderr


@pytest.mark.timeout(60)
@pytest.mark.skipif(not shutil.which("git"), reason="git is not installed")
def test_git_sends_token_as_password_on_the_wire(auth_probe, monkeypatch):
    """The URL git_path builds arrives as 'x-access-token:<token>', not '<token>:'."""
    port, seen = auth_probe
    monkeypatch.setenv("GITHUB_TOKEN", "tok123")

    resolver = GitResolver("test", None, "git+https://github.com/owner/repo.git", "main")
    userinfo = urlparse(resolver.git_path).netloc.rpartition("@")[0]

    stderr = _probe_git(port, userinfo)

    assert seen[-1] == "Basic " + base64.b64encode(b"x-access-token:tok123").decode()
    # Reached the server and was refused, rather than dying for want of a prompt.
    assert "Authentication failed" in stderr
    assert "could not read Password" not in stderr


@pytest.mark.timeout(60)
@pytest.mark.skipif(not shutil.which("git"), reason="git is not installed")
def test_git_empty_password_form_does_not_prompt(auth_probe, monkeypatch):
    """
    An unrecognised host sends the same bytes as before but does not prompt.

    'tok123@host' and 'tok123:@host' are byte-identical on the wire. The colon is
    what tells git a password was supplied, so a refusal ends there instead of
    falling through to a prompt that a machine with no terminal cannot answer.
    """
    port, seen = auth_probe
    monkeypatch.setenv("GIT_TOKEN", "tok123")

    resolver = GitResolver("test", None, "git+https://git.example.com/owner/repo.git", "main")
    userinfo = urlparse(resolver.git_path).netloc.rpartition("@")[0]
    assert userinfo == "tok123:"

    stderr = _probe_git(port, userinfo)

    assert seen[-1] == "Basic " + base64.b64encode(b"tok123:").decode()
    assert "Authentication failed" in stderr
    assert "could not read Password" not in stderr


@pytest.mark.timeout(60)
@pytest.mark.skipif(not shutil.which("git"), reason="git is not installed")
def test_git_bare_username_form_is_the_defect(auth_probe):
    """
    Pins the behaviour that made this a defect, so the reasoning stays checkable.

    The old form sends exactly what the new one does and then, when refused, has
    nowhere left to go. With prompting disabled that surfaces as a terminal
    error; on a CI runner it was an ENXIO on /dev/tty.
    """
    port, seen = auth_probe

    stderr = _probe_git(port, "tok123")

    assert seen[-1] == "Basic " + base64.b64encode(b"tok123:").decode()
    assert "could not read Password" in stderr


def test_git_resolver_resolve_remote_success(monkeypatch):
    """Test resolve_remote clones repository successfully."""
    resolver = GitResolver("test", Project("testproj"), "git://github.com/owner/repo.git", "main")

    mock_repo = MagicMock()
    mock_repo.submodules = []

    import siliconcompiler.package.git as git_module
    with patch.object(git_module, "Repo") as mock_repo_class:
        mock_repo_class.clone_from.return_value = mock_repo
        resolver.resolve_remote()

        mock_repo_class.clone_from.assert_called_once()
        mock_repo.git.checkout.assert_called_once_with("main")


def test_git_resolver_resolve_remote_with_submodules(monkeypatch):
    """Test resolve_remote initializes submodules."""
    resolver = GitResolver("test", Project("testproj"), "git://github.com/owner/repo.git", "main")

    mock_submodule = MagicMock()
    mock_repo = MagicMock()
    mock_repo.submodules = [mock_submodule]

    import siliconcompiler.package.git as git_module
    with patch.object(git_module, "Repo") as mock_repo_class, \
         patch.object(GitResolver, "_repo_uses_submodules", return_value=True):
        mock_repo_class.clone_from.return_value = mock_repo
        resolver.resolve_remote()

        mock_submodule.update.assert_called_once()


def test_git_resolver_resolve_remote_skips_submodules_when_absent(monkeypatch):
    """Test resolve_remote skips submodule update when .gitmodules is missing."""
    resolver = GitResolver("test", Project("testproj"), "git://github.com/owner/repo.git", "main")

    mock_submodule = MagicMock()
    mock_repo = MagicMock()
    mock_repo.submodules = [mock_submodule]

    import siliconcompiler.package.git as git_module
    with patch.object(git_module, "Repo") as mock_repo_class, \
         patch.object(GitResolver, "_repo_uses_submodules", return_value=False):
        mock_repo_class.clone_from.return_value = mock_repo
        resolver.resolve_remote()

        mock_submodule.update.assert_not_called()


def test_git_resolver_repo_uses_submodules_no_file(tmp_path):
    assert GitResolver._repo_uses_submodules(str(tmp_path)) is False


def test_git_resolver_repo_uses_submodules_present(tmp_path):
    (tmp_path / ".gitmodules").write_text("[submodule \"x\"]\n  path = x\n  url = ./x\n")
    assert GitResolver._repo_uses_submodules(str(tmp_path)) is True


def test_git_resolver_resolve_remote_ssh_auth_error(monkeypatch):
    """Test resolve_remote handles SSH authentication errors."""
    resolver = GitResolver("test", None, "git+ssh://git@github.com/owner/repo.git", "main")

    import siliconcompiler.package.git as git_module
    from git.exc import GitCommandError

    # Create GitCommandError that will show 'Permission denied' in repr
    error = GitCommandError("git", "clone", stderr="Permission denied")

    with patch.object(git_module, "Repo") as mock_repo_class:
        mock_repo_class.clone_from.side_effect = error
        with pytest.raises(RuntimeError, match="SSH"):
            resolver.resolve_remote()


def test_git_resolver_resolve_remote_https_auth_error(monkeypatch):
    """Test resolve_remote handles HTTPS authentication errors."""
    resolver = GitResolver("test", None, "git+https://github.com/owner/repo.git", "main")

    import siliconcompiler.package.git as git_module
    from git.exc import GitCommandError

    # Create GitCommandError that will show 'could not read Username' in repr
    error = GitCommandError("git", "clone", stderr="could not read Username")

    with patch.object(git_module, "Repo") as mock_repo_class:
        mock_repo_class.clone_from.side_effect = error
        with pytest.raises(RuntimeError, match="token"):
            resolver.resolve_remote()


def test_git_resolver_resolve_remote_other_error(monkeypatch):
    """Test resolve_remote re-raises non-auth Git errors."""
    resolver = GitResolver("test", None, "git://github.com/owner/repo.git", "main")

    import siliconcompiler.package.git as git_module

    # Create a mock that raises with a generic error
    def raise_other_error(*args, **kwargs):
        from git.exc import GitCommandError
        raise GitCommandError("git", "clone", stderr=b"some other error")

    with patch.object(git_module, "Repo") as mock_repo_class:
        mock_repo_class.clone_from = raise_other_error
        with pytest.raises(Exception):  # Will raise GitCommandError
            resolver.resolve_remote()


def test_git_resolver_include_submodule_default():
    resolver = GitResolver("test", None, "git://github.com/owner/repo.git", "main")
    assert resolver.include_submodules is True
    assert resolver.git_path == "https://github.com/owner/repo.git"


def test_git_resolver_include_submodule_default_with_qs():
    resolver = GitResolver("test", None, "git://github.com/owner/repo.git?somethingelse=False",
                           "main")
    assert resolver.include_submodules is True
    assert resolver.git_path == "https://github.com/owner/repo.git"


def test_git_resolver_include_submodule_invalid():
    resolver = GitResolver("test", None, "git://github.com/owner/repo.git?submodules=k", "main")
    with pytest.raises(ValueError, match=r"^k is not a valid option for submodules$"):
        resolver.include_submodules


@pytest.mark.parametrize("scheme,expect", (("ssh", "ssh"), ("git+ssh", "ssh"),
                                           ("git", "https"), ("git+https", "https")))
@pytest.mark.parametrize("value", ("False", "FALSE", "false", "f", "F", "0"))
def test_git_resolver_include_submodule_false(scheme, expect, value):
    resolver = GitResolver("test", None, f"{scheme}://github.com/owner/repo.git?submodules={value}",
                           "main")
    assert resolver.include_submodules is False
    assert resolver.git_path == f"{expect}://github.com/owner/repo.git"


@pytest.mark.parametrize("value", ("True", "TRUE", "true", "t", "T", "1"))
def test_git_resolver_include_submodule_true(value):
    resolver = GitResolver("test", None, f"git://github.com/owner/repo.git?submodules={value}",
                           "main")
    assert resolver.include_submodules is True
    assert resolver.git_path == "https://github.com/owner/repo.git"


# ============================================================================
# Git LFS Tests
# ============================================================================


def test_git_resolver_include_lfs_default():
    resolver = GitResolver("test", None, "git://github.com/owner/repo.git", "main")
    assert resolver.include_lfs is True


def test_git_resolver_include_lfs_default_with_qs():
    resolver = GitResolver("test", None, "git://github.com/owner/repo.git?somethingelse=False",
                           "main")
    assert resolver.include_lfs is True


def test_git_resolver_include_lfs_invalid():
    resolver = GitResolver("test", None, "git://github.com/owner/repo.git?lfs=k", "main")
    with pytest.raises(ValueError, match=r"^k is not a valid option for lfs$"):
        resolver.include_lfs


@pytest.mark.parametrize("scheme,expect", (("ssh", "ssh"), ("git+ssh", "ssh"),
                                           ("git", "https"), ("git+https", "https")))
@pytest.mark.parametrize("value", ("False", "FALSE", "false", "f", "F", "0"))
def test_git_resolver_include_lfs_false(scheme, expect, value):
    resolver = GitResolver("test", None, f"{scheme}://github.com/owner/repo.git?lfs={value}",
                           "main")
    assert resolver.include_lfs is False
    assert resolver.git_path == f"{expect}://github.com/owner/repo.git"


@pytest.mark.parametrize("value", ("True", "TRUE", "true", "t", "T", "1"))
def test_git_resolver_include_lfs_true(value):
    resolver = GitResolver("test", None, f"git://github.com/owner/repo.git?lfs={value}",
                           "main")
    assert resolver.include_lfs is True
    assert resolver.git_path == "https://github.com/owner/repo.git"


def test_git_resolver_repo_uses_lfs_no_attributes(tmp_path):
    assert GitResolver._repo_uses_lfs(str(tmp_path)) is False


def test_git_resolver_repo_uses_lfs_no_filter(tmp_path):
    (tmp_path / ".gitattributes").write_text("*.txt text\n")
    assert GitResolver._repo_uses_lfs(str(tmp_path)) is False


def test_git_resolver_repo_uses_lfs_detects_filter(tmp_path):
    (tmp_path / ".gitattributes").write_text(
        "*.bin filter=lfs diff=lfs merge=lfs -text\n")
    assert GitResolver._repo_uses_lfs(str(tmp_path)) is True


def test_git_resolver_pull_lfs_skipped_when_not_used(tmp_path):
    """_pull_lfs is a no-op when the repo has no LFS-tracked files."""
    resolver = GitResolver("test", Project("testproj"),
                           "git://github.com/owner/repo.git", "main")
    mock_repo = MagicMock()
    mock_repo.working_dir = str(tmp_path)
    resolver._pull_lfs(mock_repo)
    mock_repo.git.lfs.assert_not_called()


def test_git_resolver_pull_lfs_invokes_when_used(tmp_path):
    """_pull_lfs calls 'git lfs pull' when .gitattributes has filter=lfs."""
    (tmp_path / ".gitattributes").write_text("*.bin filter=lfs\n")

    resolver = GitResolver("test", Project("testproj"),
                           "git://github.com/owner/repo.git", "main")
    mock_repo = MagicMock()
    mock_repo.working_dir = str(tmp_path)
    resolver._pull_lfs(mock_repo)
    mock_repo.git.lfs.assert_called_once_with("pull")


def test_git_resolver_pull_lfs_missing_binary(tmp_path):
    """_pull_lfs raises RuntimeError if git-lfs is not installed."""
    (tmp_path / ".gitattributes").write_text("*.bin filter=lfs\n")

    resolver = GitResolver("test", Project("testproj"),
                           "git://github.com/owner/repo.git", "main")

    from git.exc import GitCommandError

    mock_repo = MagicMock()
    mock_repo.working_dir = str(tmp_path)
    mock_repo.git.lfs.side_effect = GitCommandError(
        "git", "lfs", stderr=b"git: 'lfs' is not a git command. See 'git --help'.")

    with pytest.raises(RuntimeError, match="git-lfs"):
        resolver._pull_lfs(mock_repo)


def test_git_resolver_pull_lfs_passthrough_other_errors(tmp_path):
    """_pull_lfs re-raises GitCommandError for non-installation failures."""
    (tmp_path / ".gitattributes").write_text("*.bin filter=lfs\n")

    resolver = GitResolver("test", Project("testproj"),
                           "git://github.com/owner/repo.git", "main")

    from git.exc import GitCommandError

    mock_repo = MagicMock()
    mock_repo.working_dir = str(tmp_path)
    mock_repo.git.lfs.side_effect = GitCommandError(
        "git", "lfs", stderr=b"network unreachable")

    with pytest.raises(GitCommandError):
        resolver._pull_lfs(mock_repo)


def test_git_resolver_resolve_remote_pulls_lfs(tmp_path):
    """resolve_remote invokes LFS pull on main repo when applicable."""
    proj = Project("testproj")
    proj.set("option", "cachedir", tmp_path)

    resolver = GitResolver("test", proj, "git://github.com/owner/repo.git", "main")

    mock_repo = MagicMock()
    mock_repo.submodules = []

    import siliconcompiler.package.git as git_module
    with patch.object(git_module, "Repo") as mock_repo_class, \
         patch.object(GitResolver, "_repo_uses_lfs", return_value=True):
        mock_repo_class.clone_from.return_value = mock_repo
        resolver.resolve_remote()
        mock_repo.git.lfs.assert_called_once_with("pull")


def test_git_resolver_resolve_remote_lfs_disabled(tmp_path):
    """resolve_remote skips LFS pull when ?lfs=false is in URL."""
    proj = Project("testproj")
    proj.set("option", "cachedir", tmp_path)

    resolver = GitResolver("test", proj,
                           "git://github.com/owner/repo.git?lfs=false", "main")

    mock_repo = MagicMock()
    mock_repo.submodules = []

    import siliconcompiler.package.git as git_module
    with patch.object(git_module, "Repo") as mock_repo_class, \
         patch.object(GitResolver, "_repo_uses_lfs", return_value=True):
        mock_repo_class.clone_from.return_value = mock_repo
        resolver.resolve_remote()
        mock_repo.git.lfs.assert_not_called()


def test_git_resolver_resolve_remote_pulls_lfs_in_submodules(tmp_path):
    """resolve_remote invokes LFS pull on submodules when both flags are on."""
    proj = Project("testproj")
    proj.set("option", "cachedir", tmp_path)

    resolver = GitResolver("test", proj, "git://github.com/owner/repo.git", "main")

    mock_submodule_repo = MagicMock()
    mock_submodule = MagicMock()
    mock_submodule.module.return_value = mock_submodule_repo

    mock_repo = MagicMock()
    mock_repo.submodules = [mock_submodule]

    import siliconcompiler.package.git as git_module
    with patch.object(git_module, "Repo") as mock_repo_class, \
         patch.object(GitResolver, "_repo_uses_lfs", return_value=True), \
         patch.object(GitResolver, "_repo_uses_submodules", return_value=True):
        mock_repo_class.clone_from.return_value = mock_repo
        resolver.resolve_remote()
        mock_repo.git.lfs.assert_called_once_with("pull")
        mock_submodule_repo.git.lfs.assert_called_once_with("pull")
