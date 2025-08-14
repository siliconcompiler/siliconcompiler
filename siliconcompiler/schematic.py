import re
import json
from types import SimpleNamespace
from typing import List, Union
from siliconcompiler.schema import BaseSchema
from siliconcompiler.schema import EditableSchema, Parameter, Scope
from siliconcompiler.schema.utils import trim

###########################################################################
class SchematicSchema(BaseSchema):
    '''
    Basic schematic entry class for designing systems with real physical
    components.

    This class inherits from :class:`~siliconcompiler.LibrarySchema` and
    :class:`~siliconcompiler.DependencySchema`, and adds parameters and
    methods specific to creating a schematic.
    '''

    def __init__(self, name: str = None):
        '''
        Initializes a new Schematic design object.

        Args:
            name (str, optional): The name of the design. Defaults to None.
        '''

        # in memory object lookup
        self.name = name
        self.parts = {}       # library parts
        self.pins = {}        # top-level pins
        self.nets = {}        # net declarations
        self.components = {}  # instantiated parts
        self.connections = {} # net: [pin refs]
        self.index = 0        # generated net name index

        # leveraging SC infrastructure as raw dictionary
        super().__init__()
        schema_schematic(self)


    ######################################################################
    def add_pin(self, name: str, direction: str, bitrange=(0,0)):
        """
        Adds pin to schematic object.

        Args:
            name (str): Pin name (e.g., "in", "sel").
            direction (str): Pin direction (input, output, or inout).
            bitrange (int, int): Pin vector range (max, min).
        """
        # local lookup table
        pin = SimpleNamespace(name=name)
        self.pins[name] = pin
        setattr(self, name, pin)

        # SC raw dictionary
        self.set('schematic', 'pin', name, 'direction', direction)
        self.set('schematic', 'pin', name, 'bitrange', bitrange)

        # return pin object
        return pin

    def get_pindir(self, name: str):
        """
        Returns direction of named pin.

        Args:
            name (str): Pin name (e.g., "in", "sel").
        Returns:
            str: Pin direction
        """
        return self.get('schematic', 'pin', name, 'direction')

    def get_pinrange(self, name: str):
        """
        Returns vector bit range of named pin.
        Args:
            name (str): Pin name.
        Returns:
            str: Pin vector bit range
        """
        return self.get('schematic', 'pin', name, 'bitrange')

    def all_pins(self):
        """
        Returns list of all schematic pins.
        """
        return self.getkeys('schematic', 'pin')

    ####################################################
    def add_part(self, name: str, pins: List[str]):
        """
        Adds part declaration.
        This is an interface/header type declaration required for all
        parts to be instantiated in the schematic.

        Args:
            name (str): Part name (e.g., NAND2).
            pins (list str): List of all part pins.
                Vector pins use bus character [] (eg. in[7:0])
        Returns:
            str: Part object
        """
        # local object database
        part = SimpleNamespace(name=name)
        self.parts[name] = part
        setattr(self, name, part)

        # make pins accessible as objects
        for pin in pins:
            setattr(part, pin, SimpleNamespace(name=pin))

        # record flat SC dictionary
        for pin in pins:
            m = re.match(r"^([^\[]+)\[(\d+):(\d+)\]$", pin)
            bitrange = (0,0)
            if m:
                pin = m.group(1)
                bitrange = (int(m.group(2)), int(m.group(3)))
            self.set('schematic', 'part', name, 'pin', pin, 'bitrange', bitrange)

        # return part object
        return part

    #####################################################
    def add_component(self, name: str, partname: str):
        """
        Adds component (instance) to the schematic object.
        Args:
            name (str): Instance name
            partname (str): Instance partname/cellname.
        Returns:
            str: Pin direction
        """
        # create component
        comp = SimpleNamespace(name=name)
        self.components[name] = comp
        setattr(self, name, comp)

        # clone part pins into component namespace
        part = self.parts[partname]
        for attr, value in vars(part).items():
            if isinstance(value, SimpleNamespace):
                setattr(comp, attr, SimpleNamespace(name=value.name))

        # SC raw dictionary
        self.set('schematic', 'component', name, 'partname', partname)

        return comp

    def get_partname(self, name: str):
        """
        Returns instance part name.
        Args:
           name (str): Instance name (e.g., "i0", "inst0", "myCell").
        Returns:
           list[str]: Instance part name
        """
        return self.get('schematic', 'component', name, 'partname')

    def all_components(self):
        """
        Returns list of all schematic components.
        """
        return self.getkeys('schematic', 'component')

    ##########################################
    def add_net(self, name, bitrange=(0,0)):
        """
        Adds named net to the schematic.
        Args:
            name (str, optional):
                 Net name
            bitrange (int, int):
                  Net vector range (max, min).
        Returns:
            str: List of pins connected to net
        """
        # local object lookup
        net = SimpleNamespace(name=name)
        self.nets[name] = net
        setattr(self, name, net)

        #  store in flat SC dictionary
        self.set('schematic', 'net', name, 'bitrange', bitrange)

        return net

    def get_netrange(self, name: str) -> List[str]:
        """
        Returns of vector bit range (max,min) of named net.
        Args:
            name (str): Net name
        Returns:
            str: Tuple (max,min) of net vector bit range.
        """
        return self.get('schematic', 'net', name, 'bitrange')

    def all_nets(self):
        """
        Returns list of all schematic nets.
        """
        return self.getkeys('schematic', 'net')

    ####################################
    def connect(self, pins, net=None):
        """
        Connect pins together.

        Args:
            pins (List[str]): Pin objects to connect
            net (str, optional): Net name
        """
        if net not in self.connections:
            self.connections[net] = []

        for pin in pins:
            self.connections[net].append(self._resolve_pin(pin))

    ####################################
    def write_verilog(self, filename):
        """
        Writes out schematic as Verilog netlist.

        Args:
            filename (str or Path):
                Path to the output netlist file.

        """
        lines = []

        # Module header
        port_list = ", ".join(self.pins.keys())
        lines.append(f"module {self.name}({port_list});\n")

        # Declare top-level pins
        for pin_name, pin in self.pins.items():
            # For now we assume all are single-bit (scalars)
            direction = self.get_pindir(pin_name)
            lines.append(f"  {direction} {pin_name};")

        lines.append("")  # blank line

        # Declare nets
        for net in self.connections:
            if net not in self.pins:
                lines.append(f"  wire {net};")

        lines.append("")  # blank line

        # Instantiate components
        for comp_name, comp in self.components.items():
            partname = self.get_partname(comp_name)
            # collect pin connections
            pin_conns = []
            for pin_attr, pin_obj in vars(comp).items():
                # find which net this pin is connected to
                net_connected = None
                for net_name, pins in self.connections.items():
                    if self._resolve_pin(pin_obj) in pins:
                        net_connected = net_name
                        break
                if net_connected:
                    pin_conns.append(f".{pin_attr}({net_connected})")
            pin_conns_str = ", ".join(pin_conns)
            lines.append(f"  {partname} {comp_name} ({pin_conns_str});")

        lines.append("\nendmodule\n")

        # Write to file
        with open(filename, "w") as f:
            f.write("\n".join(lines))



    ###################################
    def read_verilog(self, filename):
        """
        Read Verilog netlist file into data structure.

        Args:
            filename (str or Path):
                Path to the output netlist file.

        """

        # TODO: use pyslang to stuff content into common data structure

    ###########################
    # Helper Functions
    ###########################
    def _resolve_pin(self, pin):
        """Convert pin object to a unique string like 'i0.a' or 'in0'."""
        if getattr(pin, "parent", None):
            return f"{pin.parent}.{pin.name}"
        return pin.name


###########################################################################
# Schema
###########################################################################
def schema_schematic(schema):
    '''
    Defines the schema parameters specific to a schematic

    This function is called by the `SchematicSchema` constructor to set up
    all schematic parameters:

    Args:
        schema (SchematicSchema): The schema object to configure.
    '''

    schema = EditableSchema(schema)

    inst = 'default'
    defpin = 'default'
    net = 'default'
    part = 'default'

    # hierarchy character
    schema.insert(
        'schematic', 'hierchar',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Schematic hierarchy character",
            example=["api: chip.set('schematic', 'hierchar', '/')"],
            help=trim("""
            Specifies the character used to express hierarchy. If
            the hierarchy character is used as part of a name, it must be
            escaped with a backslash('\').""")))

    # bus character
    schema.insert(
        'schematic', 'buschar',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Schematic bus character",
            example=["api: chip.set('schematic', 'buschar', '[]')"],
            help=trim("""
            Specifies the character used to express bus bits. If the
            bus character is used as part of a name, it must be
            escaped with a backslash('\').""")))

    # pin direction
    schema.insert(
        'schematic', 'pin', defpin, 'direction',
        Parameter(
            '<input,output,inout>',
            scope=Scope.GLOBAL,
            shorthelp="Pin direction",
            example=[
                "api: chip.set('schematic','pin', 'A', 'direction', 'input')"],
            help=trim("""
            Direction of pin specified on a per pin basis.""")))

    # pin vector size
    schema.insert(
        'schematic', 'pin', defpin, 'bitrange',
        Parameter(
            '(int,int)',
            scope=Scope.GLOBAL,
            shorthelp="Pin bitrange",
            example=[
                "api: chip.set('schematic','pin', 'A', 'bitrange', (7,0)"],
            help=trim("""
            Pin vector size, specified as a (max,min) tuple. A range of (0,0)
            indicates a scalar single bit pin.""")))

    # net declarations
    schema.insert(
        'schematic', 'net', net, 'bitrange',
        Parameter(
            '(int,int)',
            scope=Scope.GLOBAL,
            shorthelp="Net bit range",
            example=[
                "api: chip.set('schematic', 'net', 'net0', 'bitrange', (7,0)"],
            help=trim("""
            Net vector bit range specifid as (max,min) tuple.""")))

    # part pin vector size ("header")
    schema.insert(
        'schematic', 'part', part, 'pin', defpin, 'bitrange',
        Parameter(
            '(int,int)',
            scope=Scope.GLOBAL,
            shorthelp="Library part pin bitrange",
            example=[
                "api: chip.set('schematic', 'part', 'INV', 'pin', 'A', 'bitrange', (7,0)"],
            help=trim("""
            Part pin vector size, specified as a (max,min) tuple. A range of (0,0)
            indicates a scalar single bit pin.""")))

    # component instantiation
    schema.insert(
        'schematic', 'component', inst, 'partname',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Component part name",
            example=[
                "api: chip.set('schematic','component','i0','partname','INV')"],
            help=trim("""
            Partname (aka cellname) of the placed component (aka instance)
            specified on a per instance basis.""")))

    # cell connections
    schema.insert(
        'schematic', 'component', inst, 'connection', defpin,
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Component pin connections",
            example=[
                "api: chip.set('schematic','component','i0','connection', 'A[0]', 'in[0]')",
                "api: chip.set('schematic','component','i0','connection', 'CLK', 'clk_in')"],
            help=trim("""
            Component pin connections. Connections to instance vectors pins are
            specified on a per bit basis. The connection point format is "INSTANCE.PIN",
            where "." is the hierarchy character. Connections without ".PIN"
            implies the connection is a primary design I/O pin.""")))


if __name__ == '__main__':

    d = SchematicSchema("hello_world")

    # add library part headers
    and2 = d.add_part("and2", ["a", "b", "z"])

    # pin declarations
    in0 = d.add_pin("in0", "input")
    in1 = d.add_pin("in1", "input")
    in2 = d.add_pin("in2", "input")
    in3 = d.add_pin("in3", "input")
    out = d.add_pin("out", "output")

    # add instances
    i0 = d.add_component("i0", "and2")
    i1 = d.add_component("i1", "and2")
    i2 = d.add_component("i2", "and2")
    i3 = d.add_component("i3", "and2")

    # add nets
    net0 = d.add_net("net0")
    net1 = d.add_net("net1")

    # wire up schematic
    d.connect(pins=i0.a, net=in0)
    d.connect(pins=i0.b, net=in1)
    d.connect(pins=i1.a, net=in2)
    d.connect(pins=i1.b, net=in3)
    d.connect(pins=i2.a, net=net0)
    d.connect(pins=i2.b, net=net1)
    d.connect(pins=i2.z, net=out)

    # write verilog
    d.write_verilog("hello_world.vg")
