import pytest
import os
import sys
from unittest import mock
from pathlib import Path
from siliconcompiler.apps import sc_install
from siliconcompiler.schema_support.record import RecordSchema
from siliconcompiler.apps.sc_install import os as os_imported


@pytest.fixture(autouse=True)
def install_mock_home(monkeypatch):
    test_dir = os.getcwd()

    def _mock_home():
        return Path(test_dir)

    monkeypatch.setattr(Path, 'home', _mock_home)
    monkeypatch.setenv("HOME", test_dir)


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
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


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
@mock.patch("subprocess.call")
def test_install_failed(call, monkeypatch, capfd):
    def return_os():
        return {
            "yosys": "yosys.sh"
        }
    monkeypatch.setattr(sc_install, '_get_tools_list', return_os)

    call.return_value = 1

    monkeypatch.setattr('sys.argv', ['sc-install', 'yosys'])
    assert sc_install.main() == 1
    call.assert_called_once()

    assert "# Failed to install: yosys" in capfd.readouterr().out


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
@mock.patch("subprocess.call")
def test_install_two_tools(call, monkeypatch, capfd):
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

    assert "# Installed: openroad, yosys" in capfd.readouterr().out


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_install_two_tools_onefail(monkeypatch, capfd):
    def return_os():
        return {
            "yosys": "yosys.sh",
            "openroad": "openroad.sh"
        }
    monkeypatch.setattr(sc_install, '_get_tools_list', return_os)

    def install_tool(tool, script, build_dir, prefix):
        if tool == "openroad":
            return False
        return True
    monkeypatch.setattr(sc_install, 'install_tool', install_tool)

    monkeypatch.setattr('sys.argv', ['sc-install', 'yosys', 'openroad'])
    assert sc_install.main() == 1

    stdout = capfd.readouterr().out
    assert "# Installed: yosys" in stdout
    assert "# Failed to install: openroad" in stdout


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_install_two_tools_onefailonepending(monkeypatch, capfd):
    def return_os():
        return {
            "yosys": "yosys.sh",
            "openroad": "openroad.sh",
            "yosys-test": "yosys-test.sh"
        }
    monkeypatch.setattr(sc_install, '_get_tools_list', return_os)

    def install_tool(tool, script, build_dir, prefix):
        if tool == "openroad":
            return False
        return True
    monkeypatch.setattr(sc_install, 'install_tool', install_tool)

    monkeypatch.setattr('sys.argv', ['sc-install', 'yosys', 'openroad', 'yosys-test'])
    assert sc_install.main() == 1

    stdout = capfd.readouterr().out
    assert "# Installed: yosys" in stdout
    assert "# Failed to install: openroad" in stdout
    assert "# Pending: yosys-test" in stdout


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
@mock.patch("subprocess.call")
def test_install_group(call, monkeypatch):
    def return_os():
        return {
            "yosys": "yosys.sh",
            "yosys-slang": "yosys-slang.sh",
            "openroad": "openroad.sh",
            "sv2v": "sv2v.sh",
            "klayout": "klayout.sh"
        }
    monkeypatch.setattr(sc_install, '_get_tools_list', return_os)

    call.return_value = 0

    monkeypatch.setattr('sys.argv', ['sc-install', '-group', 'asic'])
    assert sc_install.main() == 0
    assert call.call_count == 5


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
@mock.patch("subprocess.call")
def test_install_groups(call, monkeypatch):
    def return_os():
        return {
            "yosys": "yosys.sh",
            "yosys-slang": "yosys-slang.sh",
            "yosys-wildebeest": "yosys-wildebeest.sh",
            "openroad": "openroad.sh",
            "sv2v": "sv2v.sh",
            "klayout": "klayout.sh",
            "vpr": "vpr.sh"
        }
    monkeypatch.setattr(sc_install, '_get_tools_list', return_os)

    call.return_value = 0

    monkeypatch.setattr('sys.argv', ['sc-install', '-group', 'asic', 'fpga'])
    assert sc_install.main() == 0
    assert call.call_count == 7


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
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


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_ld_library_path_msg_set(monkeypatch, capfd):
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
    monkeypatch.setenv("LD_LIBRARY_PATH", os.path.join(prefix_path, "lib"))
    assert sc_install.main() == 0

    assert "LD_LIBRARY_PATH" not in capfd.readouterr().out


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_ld_library_path_msg_set_env(monkeypatch, capfd):
    def return_os():
        return {
            "yosys": "yosys.sh"
        }
    monkeypatch.setattr(sc_install, '_get_tools_list', return_os)

    def tool_install(tool, script, build_dir, prefix):
        return True
    monkeypatch.setattr(sc_install, 'install_tool', tool_install)

    monkeypatch.setattr('sys.argv', ['sc-install', 'yosys'])
    monkeypatch.setenv("PATH", "$HOME/.local/bin")
    monkeypatch.setenv("LD_LIBRARY_PATH", "$HOME/.local/lib")
    assert sc_install.main() == 0

    o = capfd.readouterr().out

    assert "LD_LIBRARY_PATH" not in o


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_ld_library_path_msg_not_set(monkeypatch, capfd):
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
    monkeypatch.delenv("LD_LIBRARY_PATH", False)
    assert sc_install.main() == 0

    assert "LD_LIBRARY_PATH" in capfd.readouterr().out


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_prefix_script(monkeypatch, datadir, capfd):
    def return_os():
        return {
            "echo": os.path.join(datadir, "echo_prefix.sh")
        }
    monkeypatch.setattr(sc_install, '_get_tools_list', return_os)

    prefix_path = os.path.abspath('testing123')

    monkeypatch.setattr('sys.argv', ['sc-install', 'echo', '-prefix', prefix_path])
    assert sc_install.main() == 0

    output = capfd.readouterr().out
    assert f"ECHO prefix: {prefix_path}" in output
    assert "USE_SUDO_INSTALL: no" in output


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_prefix_script_use_sudo_access(monkeypatch, datadir, capfd):
    def return_os():
        return {
            "echo": os.path.join(datadir, "echo_prefix.sh")
        }
    monkeypatch.setattr(sc_install, '_get_tools_list', return_os)

    def dummmy_access(*args):
        return False
    monkeypatch.setattr(os_imported, "access", dummmy_access)

    prefix_path = os.path.abspath('testing123')

    monkeypatch.setattr('sys.argv', ['sc-install', 'echo', '-prefix', prefix_path])
    assert sc_install.main() == 0

    output = capfd.readouterr().out
    assert f"ECHO prefix: {prefix_path}" in output
    assert "USE_SUDO_INSTALL: yes" in output


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_prefix_script_use_sudo_makedirs(monkeypatch, datadir, capfd):
    def return_os():
        return {
            "echo": os.path.join(datadir, "echo_prefix.sh")
        }
    monkeypatch.setattr(sc_install, '_get_tools_list', return_os)

    def dummmy_makedirs(*args, **kwargs):
        raise PermissionError
    monkeypatch.setattr(os_imported, "makedirs", dummmy_makedirs)

    prefix_path = os.path.abspath('testing123')

    monkeypatch.setattr('sys.argv', ['sc-install', 'echo', '-prefix', prefix_path])
    assert sc_install.main() == 0

    output = capfd.readouterr().out
    assert f"ECHO prefix: {prefix_path}" in output
    assert "USE_SUDO_INSTALL: yes" in output


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
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


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_no_tool_os(monkeypatch):
    def return_os():
        return {}
    monkeypatch.setattr(sc_install, '_get_tools_list', return_os)

    monkeypatch.setattr('sys.argv', ['sc-install', 'yosys'])

    with pytest.raises(SystemExit):
        sc_install.main()


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
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
    monkeypatch.setattr(RecordSchema, "get_machine_information", os_info)
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
    monkeypatch.setattr(RecordSchema, "get_machine_information", os_info)
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
    monkeypatch.setattr(RecordSchema, "get_machine_information", os_info)
    monkeypatch.setattr('sys.argv', ['sc-install', '-debug_machine'])

    assert sc_install.main() == 1

    output = capsys.readouterr()
    assert "Unsupported operating system" in output.err
    assert f"System:    {sys}" in output.out
    assert f"Distro:    {dist}" in output.out
    assert f"Version:   {ver}" in output.out
    assert "Mapped OS: None" in output.out


@pytest.mark.parametrize('sys,dist,ver', [
    ('linux', 'dummyos', '20'),
    ('win32', 'dummyos', '20'),
    ('macos', 'dummyos', '20'),
])
def test_debug_machine_unsupported_install(monkeypatch, capsys, sys, dist, ver):
    def os_info():
        return {
            "system": sys,
            "distro": dist,
            "osversion": ver
        }
    monkeypatch.setattr(RecordSchema, "get_machine_information", os_info)
    monkeypatch.setattr('sys.argv', ['sc-install', 'yosys'])

    assert sc_install.main() == 1

    output = capsys.readouterr()
    assert "Unsupported operating system" in output.err
    assert f"System:    {sys}" in output.out
    assert f"Distro:    {dist}" in output.out
    assert f"Version:   {ver}" in output.out
    assert "Mapped OS: None" in output.out


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_groups(monkeypatch):
    def os_info_name():
        return "<os>"
    monkeypatch.setattr(sc_install, '_get_os_name', os_info_name)

    def get_plugins(*_args, **_kwargs):
        return [sc_install.get_install_groups]
    monkeypatch.setattr(sc_install, "get_plugins", get_plugins)

    tools_asic = ("sv2v", "yosys", "yosys-slang", "openroad", "klayout")
    tools_fpga = ("sv2v", "yosys", "yosys-slang", "vpr", "yosys-wildebeest")

    recommend = sc_install._recommended_tool_groups(tools_asic)
    assert 'asic' in recommend
    assert set(tools_asic) == set(recommend['asic'])

    assert 'fpga' in recommend
    assert recommend["fpga"] == "fpga group is not available for "\
        "<os> due to lack of support for the following tools: vpr"\
        ", yosys-wildebeest"

    recommend = sc_install._recommended_tool_groups(tools_fpga)
    assert 'fpga' in recommend
    assert set(tools_fpga) == set(recommend['fpga'])

    assert 'asic' in recommend
    assert recommend["asic"] == "asic group is not available for "\
        "<os> due to lack of support for the following tools: klayout, openroad"

    recommend = sc_install._recommended_tool_groups(tools_asic + tools_fpga)
    assert 'asic' in recommend
    assert set(tools_asic) == set(recommend['asic'])
    assert 'fpga' in recommend
    assert set(tools_fpga) == set(recommend['fpga'])


@pytest.mark.skipif(sys.platform != "linux", reason="only works on linux")
def test_show(monkeypatch, capsys, scroot):
    file_path = os.path.join(
        scroot,
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


def test_get_tools_list(monkeypatch):
    def get_plugins(*_args, **_kwargs):
        def tools0(osname):
            return {"tool0": "script0.sh", "tool1": "script1.sh"}

        def tools1(osname):
            return {"tool2": "script2.sh", "tool3": "script3.sh"}
        return [tools0, tools1]
    monkeypatch.setattr(sc_install, "get_plugins", get_plugins)
    assert sc_install._get_tools_list() == {
        "tool0": "script0.sh",
        "tool1": "script1.sh",
        "tool2": "script2.sh",
        "tool3": "script3.sh"
    }
