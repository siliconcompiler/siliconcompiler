import pytest
import filecmp
from pathlib import Path
from siliconcompiler import Schematic


def hello_world():
    # program to illustrate API/use case
    d = Schematic("top")

    # d.add_part(name, pinlist)
    and2 = d.add_part("and2", ["a", "b", "z"])

    # pin declarations
    # d.add_pin(name, direction)
    in0 = d.add_pin("in0", "input")
    in1 = d.add_pin("in1", "input")
    in2 = d.add_pin("in2", "input")
    in3 = d.add_pin("in3", "input")
    out = d.add_pin("out", "output")

    # add instances
    # d.d_component(inst, partname)
    i0 = d.add_component("i0", and2)
    i1 = d.add_component("i1", and2)
    i2 = d.add_component("i2", and2)

    # add nets
    net0 = d.add_net("net0")
    net1 = d.add_net("net1")

    # wire up schematic
    # d.connect(src, dst)
    d.connect(in0, i0.a)
    d.connect(in1, i0.b)
    d.connect(in2, i1.a)
    d.connect(in3, i1.b)
    d.connect(i0.z, i2.a, net0)
    d.connect(i1.z, i2.b, net1)
    d.connect(i2.z, out)

    return d


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
    pin0 = d.add_pin("pin0", "output")
    assert d.get_pindir("pin0") == "output"
    assert d.get_pindir(pin0) == "output"

    pin1 = d.add_pin("pin1", "input")
    assert d.get_pindir("pin1") == "input"
    assert d.get_pindir(pin1) == "input"

    pin2 = d.add_pin("pin2", "inout")
    assert d.get_pindir("pin2") == "inout"
    assert d.get_pindir(pin2) == "inout"

    # vector check
    bus = d.add_pin("bus[7:0]", "output")
    assert d.get_pinrange("bus") == (7, 0)
    assert d.get_pinrange(bus) == (7, 0)

    # scalar check
    assert d.get_pinrange("pin0") == (0, 0)
    assert d.get_pinrange(pin0) == (0, 0)

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
    assert d.get_netrange(net0) == (0, 0)

    bus0 = d.add_net("bus0[7:0]")
    assert d.get_netrange(bus0) == (7, 0)


def test_all_nets():
    d = Schematic("test")

    d.add_net("net0")
    d.add_net("net1")

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
    d.add_component("i0", nand2)
    d.add_component("i1", nand2)
    assert d.all_components() == ('i0', 'i1')


def test_connect():

    d = hello_world()

    assert d.get('schematic', 'component', 'i0', 'connection', 'a') == 'in0'
    assert d.get('schematic', 'component', 'i0', 'connection', 'b') == 'in1'
    assert d.get('schematic', 'component', 'i0', 'connection', 'z') == 'net0'
    assert d.get('schematic', 'component', 'i1', 'connection', 'a') == 'in2'
    assert d.get('schematic', 'component', 'i1', 'connection', 'b') == 'in3'
    assert d.get('schematic', 'component', 'i1', 'connection', 'z') == 'net1'
    assert d.get('schematic', 'component', 'i2', 'connection', 'a') == 'net0'
    assert d.get('schematic', 'component', 'i2', 'connection', 'b') == 'net1'
    assert d.get('schematic', 'component', 'i2', 'connection', 'z') == 'out'


def test_write_verilog():
    test_dir = Path(__file__).parent
    golden_file = test_dir / "data" / "schematic.vg"
    d = hello_world()
    d.write_verilog("test.v")
    assert filecmp.cmp("test.vg", golden_file)
