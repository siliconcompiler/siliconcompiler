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


def test_debug_machine_supported(monkeypatch, capsys):
    def os_info():
        return {
            "system": "linux",
            "distro": "ubuntu",
            "osversion": "24.04"
        }
    monkeypatch.setattr(sc_install, '_get_machine_info', os_info)
    monkeypatch.setattr('sys.argv', ['sc-install', '-debug_machine'])

    assert sc_install.main() == 0

    output = capsys.readouterr().out
    assert "System:    linux" in output
    assert "Distro:    ubuntu" in output
    assert "Version:   24.04" in output
    assert "Mapped OS: ubuntu24" in output
    assert "Scripts:   " in output


def test_debug_machine_remapped(monkeypatch, capsys):
    def os_info():
        return {
            "system": "linux",
            "distro": "rocky",
            "osversion": "8.10"
        }
    monkeypatch.setattr(sc_install, '_get_machine_info', os_info)
    monkeypatch.setattr('sys.argv', ['sc-install', '-debug_machine'])

    assert sc_install.main() == 0

    output = capsys.readouterr().out
    assert "System:    linux" in output
    assert "Distro:    rocky" in output
    assert "Version:   8.10" in output
    assert "Mapped OS: rhel8" in output


@pytest.mark.parametrize('sys,dist,ver', [
    ('linux', 'dummyos', '20'),
    ('win32', 'dummyos', '20'),
    ('macos', 'dummyos', '20'),
])
def test_debug_machine_unsupported(monkeypatch, capsys, sys, dist, ver):
    def os_info():
        return {
            "system": sys,
            "distro": dist,
            "osversion": ver
        }
    monkeypatch.setattr(sc_install, '_get_machine_info', os_info)
    monkeypatch.setattr('sys.argv', ['sc-install', '-debug_machine'])

    assert sc_install.main() == 0

    output = capsys.readouterr().out
    assert f"System:    {sys}" in output
    assert f"Distro:    {dist}" in output
    assert f"Version:   {ver}" in output
    assert "Mapped OS: None" in output


def test_groups():
    tools_asic = ("surelog", "sv2v", "yosys", "openroad", "klayout")
    tools_fpga = ("surelog", "sv2v", "yosys", "vpr")

    recommend = sc_install._recommended_tool_groups(tools_asic)
    assert 'asic' in recommend
    assert set(tools_asic) == set(recommend['asic'])

    assert 'fpga' not in recommend

    recommend = sc_install._recommended_tool_groups(tools_fpga)
    assert 'fpga' in recommend
    assert set(tools_fpga) == set(recommend['fpga'])

    assert 'asic' not in recommend

    recommend = sc_install._recommended_tool_groups(tools_asic + tools_fpga)
    assert 'asic' in recommend
    assert set(tools_asic) == set(recommend['asic'])
    assert 'fpga' in recommend
    assert set(tools_fpga) == set(recommend['fpga'])


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
