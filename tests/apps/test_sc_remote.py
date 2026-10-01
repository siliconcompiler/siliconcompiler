import itertools
import os
import pytest

from pathlib import Path

from siliconcompiler.apps import sc_remote


# What is left here is what tests the app wrapper rather than the client: the
# argument shape, which is not being rewritten. Everything else in this file
# drove the pre-v1 client through the CLI and is captured in
# tests/remote/BEHAVIOUR.md, section F.


@pytest.fixture(autouse=True)
def patch_home(monkeypatch):
    def new_home():
        return os.getcwd()
    monkeypatch.setattr(Path, 'home', new_home)


@pytest.mark.parametrize("args", list(itertools.permutations(
        ['configure', 'reconnect', 'cancel', 'delete'], r=2)))
def test_exclusive_args(args, monkeypatch):
    monkeypatch.setattr('sys.argv', ['sc-remote',
                                     f'-{args[0]}',
                                     f'-{args[1]}'])

    assert sc_remote.main() == 1


@pytest.mark.parametrize("arg", ['reconnect', 'cancel', 'delete'])
def test_require_cfg(arg, monkeypatch):
    monkeypatch.setattr('sys.argv', ['sc-remote',
                                     f'-{arg}'])

    assert sc_remote.main() == 2


@pytest.mark.parametrize("arg", ['reconnect', 'cancel', 'delete'])
def test_server_beside_a_job_command_stops_there(arg, monkeypatch):
    '''Refused, and nothing after it runs: the job's own manifest says which
    server it went to.'''
    def reached(*args, **kwargs):
        raise AssertionError("a client was made after the refusal")

    monkeypatch.setattr(sc_remote, "Client", reached)
    monkeypatch.setattr('sys.argv', ['sc-remote', f'-{arg}', '-cfg', 'job.pkg.json',
                                     '-server', 'https://sc-server.test'])

    assert sc_remote.main() == 2


def test_an_unreachable_server_is_reported_not_raised(monkeypatch, caplog):
    '''A refusal is a message and an exit code, never a traceback.'''
    monkeypatch.setattr('sys.argv', ['sc-remote',
                                     '-credentials', 'sc-auth/remote.json',
                                     '-configure',
                                     '-server', 'https://127.0.0.1:1/'])

    assert sc_remote.main() != 0
    assert caplog.text


def test_a_missing_manifest_names_the_path(monkeypatch, caplog):
    '''F9: an absent -cfg manifest is an error with the path in it.'''
    monkeypatch.setattr('sys.argv', ['sc-remote',
                                     '-credentials', 'sc-auth/remote.json',
                                     '-cancel',
                                     '-cfg', 'nowhere.json'])

    assert sc_remote.main() == 1
    assert 'nowhere.json' in caplog.text


def test_a_manifest_with_no_job_is_refused(monkeypatch, caplog):
    '''A manifest that was never submitted names no job to act on, and saying
    so here is cheaper than a 404 from a server that was never asked.'''
    Path('manifest.json').write_text('{}')
    monkeypatch.setattr('sys.argv', ['sc-remote',
                                     '-credentials', 'sc-auth/remote.json',
                                     '-cancel',
                                     '-cfg', 'manifest.json'])

    assert sc_remote.main() == 1
    assert 'no remote job is recorded beside' in caplog.text
