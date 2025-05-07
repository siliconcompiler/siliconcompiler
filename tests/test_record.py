import distro
import platform
import getpass
import psutil
import pytest
import socket

from datetime import datetime, timezone
from unittest.mock import patch
from unittest import mock

import pip._internal.operations.freeze

from siliconcompiler import _metadata

from siliconcompiler.record import RecordSchema, RecordTime, RecordTool


@pytest.fixture()
def mock_datetime_now(monkeypatch):
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.utcnow.return_value = datetime(2020, 3, 11, 14, 0, 0, tzinfo=timezone.utc)
        mock_datetime.strptime = datetime.strptime
        yield


def test_keys():
    assert sorted(RecordSchema().getkeys()) == sorted([
        'userid',
        'publickey',
        'machine',
        'macaddr',
        'ipaddr',
        'platform',
        'distro',
        'arch',
        'starttime',
        'endtime',
        'region',
        'scversion',
        'toolversion',
        'toolpath',
        'toolargs',
        'pythonversion',
        'osversion',
        'kernelversion',
        'toolexitcode',
        'remoteid',
        'pythonpackage',
        'status',
        'inputnode',
    ])


def test_clear():
    schema = RecordSchema()

    schema.record_time("teststep", "testindex", RecordTime.START)
    assert schema.get("starttime", step="teststep", index="testindex") is not None

    schema.clear("teststep", "thisthisindex")
    assert schema.get("starttime", step="teststep", index="testindex") is not None

    schema.clear("teststep", "testindex")
    assert schema.get("starttime", step="teststep", index="testindex") is None


def test_clear_keep():
    schema = RecordSchema()

    schema.record_time("teststep", "testindex", RecordTime.START)
    assert schema.get("starttime", step="teststep", index="testindex") is not None

    schema.clear("teststep", "testindex", keep=["starttime"])
    assert schema.get("starttime", step="teststep", index="testindex") is not None


@pytest.mark.parametrize("type", (RecordTime.START, RecordTime.END))
def test_record_time(type, mock_datetime_now):
    schema = RecordSchema()

    assert schema.get(type.value, step="teststep", index="testindex") is None
    assert schema.record_time("teststep", "testindex", type) == 1583935200.0
    assert schema.get(type.value, step="teststep", index="testindex") == '2020-03-11 14:00:00'


@pytest.mark.parametrize("type", (RecordTime.START, RecordTime.END))
def test_get_recorded_time(type, mock_datetime_now):
    schema = RecordSchema()

    assert schema.get(type.value, step="teststep", index="testindex") is None
    assert schema.record_time("teststep", "testindex", type) == 1583935200.0
    assert schema.get_recorded_time("teststep", "testindex", type) == 1583935200.0


def test_record_python_packages(monkeypatch):
    def fake_freeze():
        return ["testpackage==1.0", "testthis==5.0"]

    monkeypatch.setattr(pip._internal.operations.freeze, "freeze", fake_freeze)
    schema = RecordSchema()
    schema.record_python_packages()
    assert schema.get("pythonpackage") == ["testpackage==1.0", "testthis==5.0"]


def test_record_version(monkeypatch):
    def python_version():
        return "3.10.0"
    monkeypatch.setattr(platform, "python_version", python_version)
    monkeypatch.setattr(_metadata, "version", "thisversion")

    schema = RecordSchema()
    schema.record_version("thisstep", "thisindex")
    assert schema.get("scversion", step="thisstep", index="thisindex") == "thisversion"
    assert schema.get("pythonversion", step="thisstep", index="thisindex") == "3.10.0"


@pytest.mark.parametrize("type,value,expect", [
    (RecordTool.EXITCODE, 5, 5),
    (RecordTool.VERSION, "1.0", "1.0"),
    (RecordTool.PATH, "/thispath/tool", "/thispath/tool"),
    (RecordTool.ARGS,
     ["-exit", "/thisscript.py", "compound argument"],
     "-exit /thisscript.py \"compound argument\""),
])
def test_record_tool(type, value, expect):
    schema = RecordSchema()
    assert schema.get(type.value, step="thisstep", index="thisindex") is None
    schema.record_tool("thisstep", "thisindex", value, type)
    assert schema.get(type.value, step="thisstep", index="thisindex") == expect


def test_record_userinformation(monkeypatch):
    monkeypatch.setattr(RecordSchema, "get_user_information", lambda: {"username": "me"})
    monkeypatch.setattr(RecordSchema, "get_cloud_information", lambda: {"region": "east"})
    monkeypatch.setattr(RecordSchema, "get_ip_information", lambda: {
        "ip": "127.0.0.1",
        "mac": "AA:BB:CC"})
    monkeypatch.setattr(RecordSchema, "get_machine_information", lambda: {
        'name': 'machinename',
        'system': "linux",
        'distro': "ubuntu",
        'osversion': "22.04",
        'kernelversion': "6.8.0",
        'arch': "x86"})
    schema = RecordSchema()
    schema.record_userinformation("thisstep", "thisindex")
    assert schema.get("userid", step="thisstep", index="thisindex") == "me"
    assert schema.get("platform", step="thisstep", index="thisindex") == "linux"
    assert schema.get("distro", step="thisstep", index="thisindex") == "ubuntu"
    assert schema.get("osversion", step="thisstep", index="thisindex") == "22.04"
    assert schema.get("kernelversion", step="thisstep", index="thisindex") == "6.8.0"
    assert schema.get("arch", step="thisstep", index="thisindex") == "x86"
    assert schema.get("machine", step="thisstep", index="thisindex") == "machinename"
    assert schema.get("region", step="thisstep", index="thisindex") == "east"
    assert schema.get("ipaddr", step="thisstep", index="thisindex") == "127.0.0.1"
    assert schema.get("macaddr", step="thisstep", index="thisindex") == "AA:BB:CC"


def test_record_userinformation_limited(monkeypatch):
    monkeypatch.setattr(RecordSchema, "get_user_information", lambda: {"username": "me"})
    monkeypatch.setattr(RecordSchema, "get_cloud_information", lambda: {"region": "east"})
    monkeypatch.setattr(RecordSchema, "get_ip_information", lambda: {
        "ip": None,
        "mac": None})
    monkeypatch.setattr(RecordSchema, "get_machine_information", lambda: {
        'name': 'machinename',
        'system': "linux",
        'distro': None,
        'osversion': "22.04",
        'kernelversion': None,
        'arch': "x86"})
    schema = RecordSchema()
    schema.record_userinformation("thisstep", "thisindex")
    assert schema.get("userid", step="thisstep", index="thisindex") == "me"
    assert schema.get("platform", step="thisstep", index="thisindex") == "linux"
    assert schema.get("distro", step="thisstep", index="thisindex") is None
    assert schema.get("osversion", step="thisstep", index="thisindex") == "22.04"
    assert schema.get("kernelversion", step="thisstep", index="thisindex") is None
    assert schema.get("arch", step="thisstep", index="thisindex") == "x86"
    assert schema.get("machine", step="thisstep", index="thisindex") == "machinename"
    assert schema.get("region", step="thisstep", index="thisindex") == "east"
    assert schema.get("ipaddr", step="thisstep", index="thisindex") is None
    assert schema.get("macaddr", step="thisstep", index="thisindex") is None


def test_get_user_information(monkeypatch):
    monkeypatch.setattr(getpass, "getuser", lambda: "thisuser")

    assert RecordSchema.get_user_information() == {
        "username": "thisuser"
    }


def test_get_cloud_information():
    assert RecordSchema.get_cloud_information() == {
        "region": "local"
    }


@pytest.mark.parametrize("system,osdistro,osversion,kernelversion,expect", [
    ("Linux", "ubuntu", "22.04", "6.8.0", {
        'arch': 'arm64',
        'distro': 'ubuntu',
        'kernelversion': '6.8.0',
        'name': 'thisname',
        'osversion': '22.04',
        'system': 'linux'}),
    ("Darwin", None, "22.04", "6.8.0", {
        'arch': 'arm64',
        'distro': None,
        'kernelversion': '6.8.0',
        'name': 'thisname',
        'osversion': '22.04',
        'system': 'macos'}),
    ("Windows", "ubuntu", "22.04", "6.8.0", {
        'arch': 'arm64',
        'distro': None,
        'kernelversion': '6.8.0',
        'name': 'thisname',
        'osversion': '6.8.0',
        'system': 'windows'})
])
def test_get_machine_information(monkeypatch, system, osdistro, osversion, kernelversion, expect):
    monkeypatch.setattr(platform, "system", lambda: system)
    monkeypatch.setattr(distro, "id", lambda: osdistro)
    monkeypatch.setattr(platform, "mac_ver", lambda: (osversion, None, None))
    monkeypatch.setattr(distro, "version", lambda: osversion)
    monkeypatch.setattr(platform, "release", lambda: kernelversion)
    monkeypatch.setattr(platform, "version", lambda: kernelversion)
    monkeypatch.setattr(platform, "node", lambda: "thisname")
    monkeypatch.setattr(platform, "machine", lambda: "arm64")
    assert RecordSchema.get_machine_information() == expect


@pytest.mark.parametrize("if_addrs,expect", [
    ({}, {'ip': None, 'mac': None}),
    ({'lo': []}, {'ip': None, 'mac': None}),
    ({'lo': [], 'eth0': []}, {'ip': None, 'mac': None}),
    ({'lo': [], 'eth0': [(socket.AF_INET, "127.0.0.1")]},
     {'ip': None, 'mac': None}),
    ({'lo': [], 'eth0': [(socket.AF_INET, "255.0.0.1")]},
     {'ip': "255.0.0.1", 'mac': None}),
    ({'lo': [], 'eth0': [(socket.AF_INET, "255.0.0.1"), (socket.AF_INET6, "255.0.0.2")]},
     {'ip': "255.0.0.1", 'mac': None}),
    ({'lo': [], 'eth0': [(socket.AF_INET6, "255.0.0.2")]},
     {'ip': "255.0.0.2", 'mac': None}),
    ({'lo': [], 'eth0': [(socket.AF_INET6, "255.0.0.2"), (psutil.AF_LINK, "AA:BB")]},
     {'ip': "255.0.0.2", 'mac': "AA:BB"}),
])
def test_get_ip_information(if_addrs, expect):
    class AddrInfo:
        def __init__(self, family, addr):
            self.family = family
            self.address = addr

    with mock.patch("psutil.net_if_addrs") as net_if_addrs:
        net_if_addrs.return_value = {
            dev: [AddrInfo(*addr) for addr in addrs]
            for dev, addrs in if_addrs.items()
        }
        assert RecordSchema.get_ip_information() == expect


def test_get_ip_information_except():
    with mock.patch("psutil.net_if_addrs") as net_if_addrs:
        def raise_except():
            raise RuntimeError
        net_if_addrs.side_effect = raise_except
        assert RecordSchema.get_ip_information() == {'ip': None, 'mac': None}
