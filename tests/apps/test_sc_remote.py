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


def test_an_unreachable_server_is_reported_not_raised(monkeypatch, caplog):
    '''A refusal is a message and an exit code, never a traceback.'''
    monkeypatch.setattr('sys.argv', ['sc-remote',
                                     '-credentials', 'creds.json',
                                     '-configure',
                                     '-server', 'https://127.0.0.1:1/'])

    assert sc_remote.main() != 0
    assert caplog.text


def test_acting_on_a_job_says_it_is_not_available_yet(monkeypatch, caplog):
    '''The job path has not landed, so every verb that needs one says so
    rather than failing somewhere further away. Delete this with phase 3.'''
    Path('manifest.json').write_text('{}')
    monkeypatch.setattr('sys.argv', ['sc-remote',
                                     '-credentials', 'creds.json',
                                     '-cancel',
                                     '-cfg', 'manifest.json'])

    assert sc_remote.main() == 1
    assert 'not available yet' in caplog.text
