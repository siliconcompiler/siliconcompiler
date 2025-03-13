import pytest
from siliconcompiler.apps import sc_server
from siliconcompiler.remote.server import Server


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
