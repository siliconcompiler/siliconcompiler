import pytest

import os.path

from siliconcompiler.apps import sc_dashboard
from siliconcompiler import Chip


def test_dashboard_no_cfg(monkeypatch):
    monkeypatch.setattr('sys.argv', ['sc-dashboard'])

    assert sc_dashboard.main() == 1


def test_dashboard_cfg(monkeypatch):
    def dashboard_run(chip, wait, port, graph_chips):
        assert wait
        assert port is None
        assert graph_chips == []

    Chip('test').write_manifest('test.json')

    monkeypatch.setattr('sys.argv', ['sc-dashboard', '-cfg', 'test.json'])
    monkeypatch.setattr(Chip, 'dashboard', dashboard_run)

    assert sc_dashboard.main() == 0


def test_dashboard_port(monkeypatch):
    def dashboard_run(chip, wait, port, graph_chips):
        assert wait
        assert port == 1000
        assert graph_chips == []

    Chip('test').write_manifest('test.json')

    monkeypatch.setattr('sys.argv', ['sc-dashboard', '-cfg', 'test.json', '-port', '1000'])
    monkeypatch.setattr(Chip, 'dashboard', dashboard_run)

    assert sc_dashboard.main() == 0


def test_dashboard_graph_cfg_file_not_found(monkeypatch):
    Chip('test').write_manifest('test.json')

    monkeypatch.setattr('sys.argv', [
        'sc-dashboard', '-cfg', 'test.json', '-graph_cfg', 'testing.json'])

    with pytest.raises(ValueError, match="not a valid file path: testing.json"):
        sc_dashboard.main()


def test_dashboard_graph_cfg(monkeypatch):
    def dashboard_run(chip, wait, port, graph_chips):
        assert wait
        assert port is None
        assert len(graph_chips) == 1
        assert graph_chips[0]["name"] == "cfg0"
        assert graph_chips[0]["cfg_path"] == os.path.abspath("test.json")

    Chip('test').write_manifest('test.json')

    monkeypatch.setattr('sys.argv', [
        'sc-dashboard', '-cfg', 'test.json', '-graph_cfg', 'test.json'])
    monkeypatch.setattr(Chip, 'dashboard', dashboard_run)

    assert sc_dashboard.main() == 0


def test_dashboard_graph_cfg_names(monkeypatch):
    def dashboard_run(chip, wait, port, graph_chips):
        assert wait
        assert port is None
        assert len(graph_chips) == 1
        assert graph_chips[0]["name"] == "testfile"
        assert graph_chips[0]["cfg_path"] == os.path.abspath("test.json")

    Chip('test').write_manifest('test.json')

    monkeypatch.setattr('sys.argv', [
        'sc-dashboard', '-cfg', 'test.json', '-graph_cfg', 'testfile', 'test.json'])
    monkeypatch.setattr(Chip, 'dashboard', dashboard_run)

    assert sc_dashboard.main() == 0


def test_dashboard_graph_cfg_names_invalid(monkeypatch):
    Chip('test').write_manifest('test.json')

    monkeypatch.setattr('sys.argv', [
        'sc-dashboard', '-cfg', 'test.json', '-graph_cfg', 'testfile', 'opt', 'test.json'])

    with pytest.raises(ValueError,
                       match='graph_cfg accepts a max of 2 values, you supplied 3 in '
                             '"-graph_cfg \\[\'testfile\', \'opt\', \'test.json\'\\]"'):
        sc_dashboard.main()
