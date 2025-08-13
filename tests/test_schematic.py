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
        ('schematic', 'pin', 'default', 'direction'),
        ('schematic', 'pin', 'default', 'bitrange'),
        ('schematic', 'component', 'default', 'partname'),
        ('schematic', 'component', 'default', 'connection', 'default'),
        ('schematic', 'net', 'default', 'bitrange')
    ])

    assert set(SchematicSchema("test").allkeys()) == golden_keys


def test_get_pindir():
    d = SchematicSchema("test")

    # passing
    d.add_pin("pin0", "output")
    d.add_pin("pin1", "input")
    d.add_pin("pin2", "inout")

    # check that pin was set correctly
    assert d.get_pindir("pin0") == "output"

    # failing testcase
    with pytest.raises(ValueError, match="error"):
        d.add_pin("input", "pin1")

def test_get_pinrange():
    d = SchematicSchema("test")

    d.add_pin("pin0", "output")
    assert d.get_pinrange("pin0") == (0,0)

    d.add_pin("pin0", "output", bitrange=(7,0))
    assert d.get_pinrange("pin0") == (7,0)

def test_all_pins():
    d = SchematicSchema("test")

    d.add_pin("pin0", "output")
    d.add_pin("pin1", "input")
    d.add_pin("pin2", "inout")

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
