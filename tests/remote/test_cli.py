import io
import os
import pytest
import requests
import responses

from pathlib import Path

from siliconcompiler.apps import sc_config
from siliconcompiler.remote import Credentials

from conftest import V1_URL


# The command's argument shape; the client itself is tested beside it.


@pytest.fixture(autouse=True)
def patch_home(monkeypatch):
    monkeypatch.setattr(Path, 'home', lambda: os.getcwd())
    monkeypatch.setenv("SC_AUTH_DIR", os.path.abspath("sc-auth"))


def main(monkeypatch, *args, command='remote'):
    monkeypatch.setattr('sys.argv', ['sc-config', command, *args])
    return sc_config.main()


def store():
    return Credentials(Path("sc-auth/remote.json"))


@pytest.mark.parametrize("error,said", [
    (requests.ConnectionError, "could not reach"), (requests.Timeout, "did not answer"),
])
def test_a_server_that_cannot_be_reached_is_reported_not_raised(
        monkeypatch, caplog, error, said):
    '''A message and a non-zero exit, never a traceback.'''
    def failed(*args, **kwargs):
        raise error()

    monkeypatch.setattr("time.sleep", lambda seconds: None)
    monkeypatch.setattr(requests.Session, "request", failed)

    assert main(monkeypatch, 'configure', 'https://sc-server.test/') == 1
    assert said in caplog.text


def test_use_and_logout_take_a_server_configured_here(monkeypatch):
    '''`use` makes one the default and `logout` forgets one; one not configured
    here is refused.'''
    for server in ("https://one.test", "https://two.test"):
        store().set_server(server)
        store().set_user_id(f"me-on-{server}")

    assert main(monkeypatch, 'use', 'https://one.test') == 0
    assert store().server == "https://one.test/v1"
    for action in ('use', 'logout'):
        assert main(monkeypatch, action, 'https://three.test') != 0
    assert main(monkeypatch, 'logout', 'https://two.test') == 0
    assert (store().server, store().servers()) == \
        ("https://one.test/v1", ["https://one.test/v1"])


def test_configure_sends_the_headers_it_is_given_and_keeps_them(
        monkeypatch, fake_v1, client_credentials):
    '''Each value is a line of standard input, never the command line, and goes with
    the first request; an empty one removes the header.'''
    fake_v1.route(responses.POST, "auth/token", client_credentials)
    fake_v1.route(responses.GET, "me", {"id": "u1", "issuer": "local"})
    server = V1_URL.rsplit("/v1", 1)[0]

    monkeypatch.setattr('sys.stdin', io.StringIO("cf-id\ncf-secret\n"))
    assert main(monkeypatch, 'configure', server, '-header', 'CF-Access-Client-Id',
                '-header', 'CF-Access-Client-Secret') == 0
    assert fake_v1.calls[0].request.headers["CF-Access-Client-Secret"] == "cf-secret"
    assert store().headers() == {"CF-Access-Client-Id": "cf-id",
                                 "CF-Access-Client-Secret": "cf-secret"}

    monkeypatch.setattr('sys.stdin', io.StringIO("\n"))
    assert main(monkeypatch, 'configure', server, '-header', 'CF-Access-Client-Secret') == 0
    assert store().headers() == {"CF-Access-Client-Id": "cf-id"}


def test_upload_directories_are_a_setting_kept_absolute(monkeypatch, settings):
    '''Each directory once, as the absolute path a collection compares.'''
    from siliconcompiler.remote.client.credentials import UPLOADS

    for change, paths in (('add', ['a', 'b']), ('add', ['a']), ('remove', ['a'])):
        assert main(monkeypatch, change, 'remote', 'uploads', *paths, command='settings') == 0
    assert UPLOADS.get() == [os.path.abspath('b')]


@pytest.mark.parametrize("job", ["01J9-job", None])
def test_fetch_follows_the_job_the_runs_manifest_names(
        monkeypatch, fake_v1, client_credentials, nop_project, job):
    '''The job is the manifest's `record,remoteid`, followed to its end and its results
    kept in the manifest; a manifest naming none is refused before the server is asked.'''
    from conftest import job_body, node_body

    store().set_server(V1_URL.rsplit("/v1", 1)[0])
    fake_v1.route(responses.POST, "auth/token", client_credentials)
    fake_v1.route(responses.GET, "jobs/01J9-job", job_body(
        "completed", nodes=[node_body("stepone", "completed"),
                            node_body("steptwo", "completed")]))
    fake_v1.route(responses.GET, "jobs/01J9-job/artifacts", {"items": []})
    if job:
        nop_project.set('record', 'remoteid', job)
    nop_project.option.set_remote(True)
    # What the scheduler writes as an interrupted run ends.
    nop_project._record_history()
    nop_project.write_manifest("gcd.pkg.json")

    assert main(monkeypatch, 'fetch', 'gcd.pkg.json') == (0 if job else 1)

    polled = [c for c in fake_v1.calls if c.request.path_url == "/v1/jobs/01J9-job"]
    assert bool(polled) is bool(job)
    # A finished run no longer asks to run remotely, in its record either.
    fetched = type(nop_project).from_manifest(filepath="gcd.pkg.json")
    assert fetched.option.get_remote() is not bool(job)
    assert fetched.history("job0").option.get_remote() is not bool(job)
