import itertools
import os
import pytest

from pathlib import Path

from siliconcompiler.apps import sc_remote


# The app wrapper's argument shape; the client itself is tested in tests/remote
# (the pre-v1 CLI behaviour is in tests/remote/BEHAVIOUR.md, section F).


@pytest.fixture(autouse=True)
def patch_home(monkeypatch):
    monkeypatch.setattr(Path, 'home', lambda: os.getcwd())


def main(monkeypatch, *args):
    monkeypatch.setattr('sys.argv', ['sc-remote', *args])
    return sc_remote.main()


@pytest.mark.parametrize("args", list(itertools.permutations(
        ['configure', 'reconnect', 'cancel', 'delete'], r=2)))
def test_exclusive_args(args, monkeypatch):
    assert main(monkeypatch, f'-{args[0]}', f'-{args[1]}') == 1


@pytest.mark.parametrize("arg", ['reconnect', 'cancel', 'delete'])
def test_require_cfg(arg, monkeypatch):
    assert main(monkeypatch, f'-{arg}') == 2


@pytest.mark.parametrize("arg", ['reconnect', 'cancel', 'delete'])
def test_server_beside_a_job_command_stops_there(arg, monkeypatch):
    '''Refused before any client is made: the job's manifest names its server.'''
    def reached(*args, **kwargs):
        raise AssertionError("a client was made after the refusal")

    monkeypatch.setattr(sc_remote, "Client", reached)
    assert main(monkeypatch, f'-{arg}', '-cfg', 'job.pkg.json',
                '-server', 'https://sc-server.test') == 2


def test_an_unreachable_server_is_reported_not_raised(monkeypatch, caplog):
    '''A refusal is a message and an exit code, never a traceback.'''
    assert main(monkeypatch, '-credentials', 'sc-auth/remote.json', '-configure',
                '-server', 'https://127.0.0.1:1/') != 0
    assert caplog.text


@pytest.mark.parametrize("manifest,said", [
    # F9: an absent manifest is named.
    (None, "nowhere.json"),
    # Never submitted, so it names no job: cheaper than a 404.
    ("{}", "no remote job is recorded beside"),
], ids=["missing", "no-job"])
def test_a_manifest_that_names_no_job_is_refused(monkeypatch, caplog, manifest, said):
    if manifest is not None:
        Path('nowhere.json').write_text(manifest)
    assert main(monkeypatch, '-credentials', 'sc-auth/remote.json', '-cancel',
                '-cfg', 'nowhere.json') == 1
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
    monkeypatch.setattr(sc_remote, "Client", lambda *args, **kwargs: Answers())
    monkeypatch.setattr(sc_remote.time, "sleep", slept.append)

    assert main(monkeypatch, '-credentials', 'sc-auth/remote.json', '-tail', 'place/0',
                '-cfg', 'job.pkg.json') == 0
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

    sc_remote._print_status(logging.getLogger("sc-remote-test"), job)

    assert all(line in caplog.text for line in said)
    assert not any(line in caplog.text for line in unsaid)
    assert "\x07" not in caplog.text and "\x1b]" not in caplog.text
