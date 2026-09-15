import pytest
from siliconcompiler.apps import sc_server
from siliconcompiler.remote import Server
from siliconcompiler.remote import server as server_module


def test_server_app(monkeypatch):
    def server_run():
        pass

    monkeypatch.setattr('sys.argv', ['sc-server'])
    monkeypatch.setattr(Server, 'run', server_run)

    sc_server.main()


def test_server_app_invalid(monkeypatch):
    def server_run():
        assert False

    monkeypatch.setattr('sys.argv', ['sc-server', '-notanoption'])
    monkeypatch.setattr(Server, 'run', server_run)

    with pytest.raises(SystemExit):
        sc_server.main()


def test_server_app_help_without_aiohttp(monkeypatch, capsys):
    # aiohttp ships in the "server" extra, but the sc-server script is
    # installed either way, so the command line has to work without it. This
    # is also what the apps reference in the docs builds from.
    monkeypatch.setattr('sys.argv', ['sc-server', '-h'])
    monkeypatch.setattr(server_module, 'missing_server_dependency', 'aiohttp')

    with pytest.raises(SystemExit) as exit:
        sc_server.main()

    assert exit.value.code == 0
    assert "sc-server" in capsys.readouterr().out


def test_server_app_run_without_aiohttp(monkeypatch, capsys):
    # Starting a server is the one thing that needs the extra, and a default
    # install has to get a message and a failing exit code, not a traceback.
    monkeypatch.setattr('sys.argv', ['sc-server'])
    monkeypatch.setattr(server_module, 'missing_server_dependency', 'aiohttp')

    assert sc_server.main() == 1

    err = capsys.readouterr().err
    assert "sc-server is unavailable" in err
    assert 'pip install "siliconcompiler[server]"' in err


def test_server_run_without_aiohttp(monkeypatch):
    monkeypatch.setattr(server_module, 'missing_server_dependency', 'aiohttp')

    with pytest.raises(ModuleNotFoundError,
                       match=r'pip install "siliconcompiler\[server\]"'):
        Server().run()
