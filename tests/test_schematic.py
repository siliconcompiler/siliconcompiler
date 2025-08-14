import pytest
import re
import shutil
import os.path
from pathlib import Path
from types import SimpleNamespace
from siliconcompiler import Schematic

def test_schematic_keys():
    golden_keys = set([
        ('schematic', 'hierchar'),
        ('schematic', 'buschar'),
        ('schematic', 'pin', 'default', 'direction'),
        ('schematic', 'pin', 'default', 'bitrange'),
        ('schematic', 'net', 'default', 'bitrange'),
        ('schematic', 'part', 'default', 'pin', 'default', 'bitrange'),
        ('schematic', 'component', 'default', 'partname'),
        ('schematic', 'component', 'default', 'connection', 'default')
    ])

    assert set(Schematic("test").allkeys()) == golden_keys


def test_add_pin():
    d = Schematic("test")

    # pindir
    pin = d.add_pin("pin", "output")
    assert d.get_pindir("pin") == "output"
    assert d.get_pindir(pin) == "output"

    pin = d.add_pin("pin", "input")
    assert d.get_pindir("pin") == "input"
    assert d.get_pindir(pin) == "input"

    pin = d.add_pin("pin", "inout")
    assert d.get_pindir("pin") == "inout"
    assert d.get_pindir(pin) == "inout"

    # vector
    bus = d.add_pin("bus[7:0]", "output")
    assert d.get_pinrange("bus") == (7,0)
    assert d.get_pinrange(bus) == (7,0)

    # scalar
    pin0 = d.add_pin("pin0", "output")
    assert d.get_pinrange("pin0") == (0,0)
    assert d.get_pinrange(pin0) == (0,0)

    # failing testcase
    with pytest.raises(ValueError, match="error"):
        pin1 = d.add_pin("input", "pin1")

def test_all_pins():
    d = Schematic("test")

    d.add_pin("pin0", "output")
    d.add_pin("pin1", "input")
    d.add_pin("pin2", "inout")

    assert d.all_pins() == ('pin0', 'pin1', 'pin2')

def test_add_net():
    d = Schematic("test")

    net0 = d.add_net("net0")
    assert d.get_netrange(net0) == (0,0)

    bus0 = d.add_net("bus0[7:0]")
    assert d.get_netrange(bus0) == (7,0)

def test_all_nets():
    d = Schematic("test")

    net0 = d.add_net("net0")
    net1 = d.add_net("net1")

    assert d.all_nets() == ("net0", "net1")

def test_add_part():
    d = Schematic("test")

    nand2 = d.add_part("NAND2", ["a", "b", "c"])

    assert d.get_partpins(nand2) == ("a", "b", "c")

def test_add_component():
    d = Schematic("test")

    nand2 = d.add_part("NAND2", ["a", "b", "c"])
    i0 = d.add_component("i0", nand2)

    assert d.get_partname(i0) == "NAND2"


def test_all_components():
    d = Schematic("test")

    nand2 = d.add_part("NAND2", ["a", "b", "c"])
    i0 = d.add_component("i0", nand2)
    i1 = d.add_component("i1", nand2)
    assert d.all_components() == ('i0', 'i1')

def test_connect():
    d = Schematic("test")

    nand2 = d.add_part("NAND2", ["a", "b", "c"])
    i0 = d.add_component("i0", nand2)
    i1 = d.add_component("i1", nand2)
    assert d.all_components() == ('i0', 'i1')
