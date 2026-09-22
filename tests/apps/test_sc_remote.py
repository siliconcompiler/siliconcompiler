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


def test_client_unavailable_is_reported(monkeypatch, caplog):
    '''The rewrite is a message and an exit code, never a traceback.

    Both halves of the remote path are absent until the v1 client lands, so
    every command that needs one has to say so rather than raising out of
    main(). Delete this test with the placeholders.
    '''
    monkeypatch.setattr('sys.argv', ['sc-remote',
                                     '-configure',
                                     '-server', 'https://example.com'])

    assert sc_remote.main() == 1
    assert 'remote execution is unavailable' in caplog.text
