import io
import os
import pytest
import requests

from pathlib import Path

from siliconcompiler.apps import sc_config
from siliconcompiler.remote import Credentials
from siliconcompiler.remote.client import cli


# The command's argument shape; the client itself is tested beside it (the
# pre-v1 CLI behaviour is in tests/remote/BEHAVIOUR.md, section F).


@pytest.fixture(autouse=True)
def patch_home(monkeypatch):
    monkeypatch.setattr(Path, 'home', lambda: os.getcwd())


def main(monkeypatch, *args):
    monkeypatch.setattr('sys.argv', ['sc-config', 'remote', *args])
    return sc_config.main()


def store():
    return Credentials(Path("sc-auth/remote.json"))


def test_an_unreachable_server_is_reported_not_raised(monkeypatch, caplog):
    '''A refusal is a message and an exit code, never a traceback.'''
    assert main(monkeypatch, 'configure', 'https://127.0.0.1:1/',
                '-credentials', 'sc-auth/remote.json') != 0
    assert caplog.text


def test_a_server_that_does_not_answer_is_reported_not_raised(monkeypatch, caplog):
    '''A request timeout is a message and a non-zero exit, not a traceback.'''
    def timed_out(*args, **kwargs):
        raise requests.Timeout()

    monkeypatch.setattr("time.sleep", lambda seconds: None)
    monkeypatch.setattr(requests.Session, "request", timed_out)

    assert main(monkeypatch, 'configure', 'https://127.0.0.1:1/',
                '-credentials', 'sc-auth/remote.json') == 1
    assert "did not answer" in caplog.text


@pytest.mark.parametrize("manifest,said", [
    # F9: an absent manifest is named.
    (None, "nowhere.json"),
    # Never submitted, so it names no job: cheaper than a 404.
    ("{}", "no remote job is recorded beside"),
], ids=["missing", "no-job"])
def test_a_manifest_that_names_no_job_is_refused(monkeypatch, caplog, manifest, said):
    if manifest is not None:
        Path('nowhere.json').write_text(manifest)
    assert main(monkeypatch, 'cancel', 'nowhere.json',
                '-credentials', 'sc-auth/remote.json') == 1
    assert said in caplog.text


@pytest.mark.parametrize("refusal,status,members,printed,waited", [
    ("not-ready", 409, {"artifact_kind": "logs"}, "live\n", [3]),
    ("feature-unsupported", 501, {"feature": "logs.stream"}, "archived\n", []),
], ids=["not-started", "no-live-log"])
def test_tail_waits_for_its_node_and_reads_the_archive_where_nothing_is_live(
        monkeypatch, capsys, refusal, status, members, printed, waited):
    '''`not-ready` is waited out; where no live log is served, the finished
    node's archived log is read instead.'''
    from siliconcompiler import Design, Project
    from siliconcompiler.remote import ServerProblem
    from siliconcompiler.remote.client.results import record_job

    class Answers:
        base_url = "https://sc-server.test"

        def __init__(self):
            self.refused = [ServerProblem(
                {"type": f"https://siliconcompiler.com/server-errors/{refusal}", **members},
                status, retry_after=3)]

        def tail_log(self, job_id, step, index, write):
            if self.refused:
                raise self.refused.pop()
            write("live\n")

        def archived_log(self, job_id, step, index):
            return "archived\n"

    Project(Design("job")).write_manifest("job.pkg.json")
    record_job(".", "j1")
    slept = []
    monkeypatch.setattr(cli, "Client", lambda *args, **kwargs: Answers())
    monkeypatch.setattr(cli.time, "sleep", slept.append)

    assert main(monkeypatch, 'tail', 'job.pkg.json', 'place/0',
                '-credentials', 'sc-auth/remote.json') == 0
    assert capsys.readouterr().out.endswith(f"\n{printed}")
    assert slept == waited


@pytest.mark.parametrize("state,extra,said,unsaid", [
    ("cancelled", {"deleted_at": "2026-09-23T10:00:00Z", "deleted_reason": "by A User",
                   "archived_at": "2026-09-24T10:00:00Z"},
     ["reason:  wrong corner", "deleted: 2026-09-23T10:00:00Z (by A User)",
      "archived: 2026-09-24T10:00:00Z"], ["error:"]),
    ("failed", {"error": {"title": "The run failed", "detail": "place/0 exited 1"}},
     ["error:   The run failed: place/0 exited 1"], ["reason:", "deleted:", "archived:"]),
], ids=["cancelled-deleted-archived", "failed"])
def test_a_jobs_status_says_why_and_what_became_of_it(caplog, state, extra, said, unsaid):
    '''A cancel's reason where no error says why; every server string loses its
    control characters.'''
    import logging

    job = {"id": "01J9-job", "state": state, "design": "gcd\x1b]0;owned\x07",
           "jobname": "job0", "created_at": "2026-09-22T10:00:00Z", "error": None,
           "deleted_at": None, "archived_at": None, "progress": {},
           "transitions": [{"state": state, "at": "2026-09-22T10:05:00Z",
                            "reason": "wrong corner"}], **extra}
    caplog.set_level(logging.INFO)

    cli._print_status(logging.getLogger("sc-config-remote-test"), job)

    assert all(line in caplog.text for line in said)
    assert not any(line in caplog.text for line in unsaid)
    assert "\x07" not in caplog.text and "\x1b]" not in caplog.text


def test_use_makes_a_configured_server_the_default(monkeypatch):
    for server in ("https://one.test", "https://two.test"):
        store().set_server(server)
        store().set_user_id(f"me-on-{server}")

    assert main(monkeypatch, 'use', 'https://one.test',
                '-credentials', 'sc-auth/remote.json') == 0
    assert store().server == "https://one.test/v1"
    assert main(monkeypatch, 'use', 'https://three.test',
                '-credentials', 'sc-auth/remote.json') != 0
    assert store().server == "https://one.test/v1"


def test_uploads_and_headers_are_added_and_removed(monkeypatch):
    '''A header's value comes from standard input, never the command line.'''
    store().set_server("https://one.test")

    assert main(monkeypatch, 'uploads', 'add', 'a', 'b',
                '-credentials', 'sc-auth/remote.json') == 0
    assert main(monkeypatch, 'uploads', 'remove', 'a',
                '-credentials', 'sc-auth/remote.json') == 0
    assert store().directory_whitelist == [os.path.abspath('b')]

    monkeypatch.setattr('sys.stdin', io.StringIO("secret\n"))
    assert main(monkeypatch, 'header', 'set', 'CF-Access-Client-Id',
                '-credentials', 'sc-auth/remote.json') == 0
    assert store().headers() == {"CF-Access-Client-Id": "secret"}
    assert main(monkeypatch, 'header', 'remove', 'CF-Access-Client-Id',
                '-credentials', 'sc-auth/remote.json') == 0
    assert store().headers() == {}


def test_import_cert_keeps_the_authority_for_configure(monkeypatch, caplog):
    '''The certificate lands in the store's own directory, its fingerprint said; a
    different one under the same name needs -overwrite.'''
    import datetime

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Our CA")])
    now = datetime.datetime.now(datetime.timezone.utc)
    first, second = (
        x509.CertificateBuilder().subject_name(name).issuer_name(name)
        .public_key(key.public_key()).serial_number(serial).not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=1)).sign(key, hashes.SHA256())
        for serial in (1, 2))
    Path("our-ca.pem").write_bytes(first.public_bytes(serialization.Encoding.PEM))

    assert main(monkeypatch, 'import-cert', 'our-ca.pem',
                '-credentials', 'sc-auth/remote.json') == 0

    assert Path("sc-auth/certs/our-ca.pem").read_bytes() == Path("our-ca.pem").read_bytes()
    assert first.fingerprint(hashes.SHA256()).hex(":").upper() in caplog.text

    Path("our-ca.pem").write_bytes(second.public_bytes(serialization.Encoding.PEM))
    assert main(monkeypatch, 'import-cert', 'our-ca.pem',
                '-credentials', 'sc-auth/remote.json') == 1
    assert main(monkeypatch, 'import-cert', 'our-ca.pem', '-overwrite',
                '-credentials', 'sc-auth/remote.json') == 0
    assert Path("sc-auth/certs/our-ca.pem").read_bytes() == Path("our-ca.pem").read_bytes()
