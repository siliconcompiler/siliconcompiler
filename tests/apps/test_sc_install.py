import pytest
import os
from unittest import mock
from siliconcompiler.apps import sc_install


@mock.patch("subprocess.call")
def test_install(call, monkeypatch):
    def return_os():
        return {
            "yosys": "yosys.sh"
        }
    monkeypatch.setattr(sc_install, '_get_tools_list', return_os)

    call.return_value = 0

    monkeypatch.setattr('sys.argv', ['sc-install', 'yosys'])
    assert sc_install.main() == 0
    call.assert_called_once()


@mock.patch("subprocess.call")
def test_install_failed(call, monkeypatch):
    def return_os():
        return {
            "yosys": "yosys.sh"
        }
    monkeypatch.setattr(sc_install, '_get_tools_list', return_os)

    call.return_value = 1

    monkeypatch.setattr('sys.argv', ['sc-install', 'yosys'])
    assert sc_install.main() == 1
    call.assert_called_once()


@mock.patch("subprocess.call")
def test_install_two_tools(call, monkeypatch):
    def return_os():
        return {
            "yosys": "yosys.sh",
            "openroad": "openroad.sh"
        }
    monkeypatch.setattr(sc_install, '_get_tools_list', return_os)

    call.return_value = 0

    monkeypatch.setattr('sys.argv', ['sc-install', 'yosys', 'openroad'])
    assert sc_install.main() == 0
    assert call.call_count == 2


@mock.patch("subprocess.call")
def test_install_group(call, monkeypatch):
    def return_os():
        return {
            "yosys": "yosys.sh",
            "openroad": "openroad.sh",
            "sv2v": "sv2v.sh",
            "surelog": "surelog.sh",
            "klayout": "klayout.sh"
        }
    monkeypatch.setattr(sc_install, '_get_tools_list', return_os)

    call.return_value = 0

    monkeypatch.setattr('sys.argv', ['sc-install', '-group', 'asic'])
    assert sc_install.main() == 0
    assert call.call_count == 5


@mock.patch("subprocess.call")
def test_install_groups(call, monkeypatch):
    def return_os():
        return {
            "yosys": "yosys.sh",
            "openroad": "openroad.sh",
            "sv2v": "sv2v.sh",
            "surelog": "surelog.sh",
            "klayout": "klayout.sh",
            "vpr": "vpr.sh"
        }
    monkeypatch.setattr(sc_install, '_get_tools_list', return_os)

    call.return_value = 0

    monkeypatch.setattr('sys.argv', ['sc-install', '-group', 'asic', 'fpga'])
    assert sc_install.main() == 0
    assert call.call_count == 6


def test_prefix(monkeypatch):
    def return_os():
        return {
            "yosys": "yosys.sh"
        }
    monkeypatch.setattr(sc_install, '_get_tools_list', return_os)

    prefix_path = os.path.abspath('testing123')

    def tool_install(tool, script, build_dir, prefix):
        assert prefix == prefix_path
        return True
    monkeypatch.setattr(sc_install, 'install_tool', tool_install)

    monkeypatch.setattr('sys.argv', ['sc-install', 'yosys', '-prefix', prefix_path])
    assert sc_install.main() == 0


@mock.patch("subprocess.call")
def test_build_dir(call, monkeypatch):
    def return_os():
        return {
            "yosys": "yosys.sh"
        }
    monkeypatch.setattr(sc_install, '_get_tools_list', return_os)

    call.return_value = 0

    build_path = os.path.abspath('testing123')

    monkeypatch.setattr('sys.argv', ['sc-install', 'yosys', '-build_dir', build_path])
    assert sc_install.main() == 0
    assert str(call.call_args.kwargs['cwd']) == os.path.join(build_path, 'yosys')


def test_no_tool_os(monkeypatch):
    def return_os():
        return {}
    monkeypatch.setattr(sc_install, '_get_tools_list', return_os)

    monkeypatch.setattr('sys.argv', ['sc-install', 'yosys'])

    with pytest.raises(SystemExit):
        sc_install.main()


def test_missing_tool(monkeypatch):
    def return_os():
        return {
            "test-tool": "test.sh"
        }
    monkeypatch.setattr(sc_install, '_get_tools_list', return_os)

    monkeypatch.setattr('sys.argv', ['sc-install', 'abc123'])

    with pytest.raises(SystemExit):
        sc_install.main()


def test_show(monkeypatch, capsys):
    file_path = os.path.join(
        os.path.dirname(__file__),
        '..',
        '..',
        'siliconcompiler',
        'toolscripts',
        'ubuntu22',
        'install-yosys.sh')

    def return_os():
        return {
            "yosys": file_path
        }
    monkeypatch.setattr(sc_install, '_get_tools_list', return_os)
    monkeypatch.setattr('sys.argv', ['sc-install', '-show', 'yosys'])

    with open(file_path) as f:
        file_content = f.read()

    assert sc_install.main() == 0
    assert file_content in capsys.readouterr().out
