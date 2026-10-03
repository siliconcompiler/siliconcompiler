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
