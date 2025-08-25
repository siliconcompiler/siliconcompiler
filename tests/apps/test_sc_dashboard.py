import pytest

from unittest.mock import patch

from siliconcompiler.apps import sc_dashboard
from siliconcompiler import Project


def test_dashboard_no_cfg(monkeypatch):
    monkeypatch.setattr('sys.argv', ['sc-dashboard'])

    assert sc_dashboard.main() == 1


def test_dashboard_cfg(monkeypatch):
    Project().write_manifest('test.json')

    monkeypatch.setattr('sys.argv', ['sc-dashboard', '-cfg', 'test.json'])

    with patch("siliconcompiler.report.dashboard.web.WebDashboard.open_dashboard") as open_dash, \
            patch("siliconcompiler.report.dashboard.web.WebDashboard.wait") as wait, \
            patch("siliconcompiler.report.dashboard.web.WebDashboard.__init__") as init:
        init.return_value = None
        assert sc_dashboard.main() == 0
        init.assert_called_once()
        open_dash.assert_called_once()
        wait.assert_called_once()

        assert init.call_args.kwargs["port"] is None
        assert init.call_args.kwargs["graph_chips"] == []


def test_dashboard_port(monkeypatch):
    Project().write_manifest('test.json')

    monkeypatch.setattr('sys.argv', ['sc-dashboard', '-cfg', 'test.json', '-port', '1000'])

    with patch("siliconcompiler.report.dashboard.web.WebDashboard.open_dashboard") as open_dash, \
            patch("siliconcompiler.report.dashboard.web.WebDashboard.wait") as wait, \
            patch("siliconcompiler.report.dashboard.web.WebDashboard.__init__") as init:
        init.return_value = None
        assert sc_dashboard.main() == 0
        init.assert_called_once()
        open_dash.assert_called_once()
        wait.assert_called_once()

        assert init.call_args.kwargs["port"] == 1000
        assert init.call_args.kwargs["graph_chips"] == []


def test_dashboard_graph_cfg_file_not_found(monkeypatch):
    Project().write_manifest('test.json')

    monkeypatch.setattr('sys.argv', [
        'sc-dashboard', '-cfg', 'test.json', '-graph_cfg', 'testing.json'])

    with pytest.raises(ValueError, match="not a valid file path: testing.json"):
        sc_dashboard.main()


def test_dashboard_graph_cfg(monkeypatch):
    Project().write_manifest('test.json')

    monkeypatch.setattr('sys.argv', [
        'sc-dashboard', '-cfg', 'test.json', '-graph_cfg', 'test.json'])

    with patch("siliconcompiler.report.dashboard.web.WebDashboard.open_dashboard") as open_dash, \
            patch("siliconcompiler.report.dashboard.web.WebDashboard.wait") as wait, \
            patch("siliconcompiler.report.dashboard.web.WebDashboard.__init__") as init:
        init.return_value = None
        assert sc_dashboard.main() == 0
        init.assert_called_once()
        open_dash.assert_called_once()
        wait.assert_called_once()

        assert init.call_args.kwargs["port"] is None
        assert len(init.call_args.kwargs["graph_chips"]) == 1


def test_dashboard_graph_cfg_names(monkeypatch):
    Project().write_manifest('test.json')

    monkeypatch.setattr('sys.argv', [
        'sc-dashboard', '-cfg', 'test.json', '-graph_cfg', 'testfile test.json'])

    with patch("siliconcompiler.report.dashboard.web.WebDashboard.open_dashboard") as open_dash, \
            patch("siliconcompiler.report.dashboard.web.WebDashboard.wait") as wait, \
            patch("siliconcompiler.report.dashboard.web.WebDashboard.__init__") as init:
        init.return_value = None
        assert sc_dashboard.main() == 0
        init.assert_called_once()
        open_dash.assert_called_once()
        wait.assert_called_once()

        assert init.call_args.kwargs["port"] is None
        assert len(init.call_args.kwargs["graph_chips"]) == 1


def test_dashboard_graph_cfg_names_invalid(monkeypatch):
    Project().write_manifest('test.json')

    monkeypatch.setattr('sys.argv', [
        'sc-dashboard', '-cfg', 'test.json', '-graph_cfg', 'testfile opt test.json'])

    with pytest.raises(ValueError,
                       match='graph_cfg accepts a max of 2 values, you supplied 3 in '
                             '"-graph_cfg \\[\'testfile\', \'opt\', \'test.json\'\\]"'):
        sc_dashboard.main()


def test_sc_dashboard_no_manifest(monkeypatch):
    monkeypatch.setattr('sys.argv', ['sc-dashboard', '-design', 'test', '-arg_step', 'invalid'])
    assert sc_dashboard.main() == 1
