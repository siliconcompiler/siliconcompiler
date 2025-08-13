import pytest
import re
import shutil
import os.path
from pathlib import Path

from siliconcompiler import SchematicSchema

def test_schematic_keys():
    golden_keys = set([
        ('schematic', 'hierchar'),
        ('schematic', 'buschar'),
        ('schematic', 'component', 'default', 'partname'),
        ('schematic', 'pin', 'default', 'direction'),
        ('schematic', 'net', 'default', 'connection')
    ])

    assert set(SchematicSchema("test").allkeys()) == golden_keys


def test_addget_pin():
    d = SchematicSchema("test")

    # passing
    assert d.add_pin("pin0", "output")
    assert d.add_pin("pin1", "input")
    assert d.add_pin("pin2", "inout")

    # check that pin was set correctly
    assert d.get_pindir("pin0") == "output"

    # failing testcase
    with pytest.raises(ValueError, match="error"):
        d.add_pin("input", "pin1")

def test_all_pins():
    d = SchematicSchema("test")

    assert d.add_pin("pin0", "output")
    assert d.add_pin("pin1", "input")
    assert d.add_pin("pin2", "inout")

    assert d.all_pins() == ('pin0', 'pin1', 'pin2')

def test_component():
    d = SchematicSchema("test")

    assert d.add_component("i0", "NAND2")
    assert d.get_partname("i0") == "NAND2"

def test_all_components():
    d = SchematicSchema("test")

    assert d.add_component("i0", "NAND2")
    assert d.add_component("i1", "NOR2")

    assert d.all_components() == ('i0', 'i1')

def test_net():
    d = SchematicSchema("test")

    assert d.connect_net("pin0", "netA")
    assert d.connect_net("pin1", "netA")

    assert d.get_net("netA") == ["pin0", "pin1"]
