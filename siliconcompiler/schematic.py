import re
from typing import List, Union, Optional, Tuple

from siliconcompiler.schema import BaseSchema
from siliconcompiler.schema import EditableSchema, Parameter, Scope
from siliconcompiler.schema.utils import trim


###########################################################################
class Pin:
    """Represents pin on component or top-level schematic."""

    def __init__(self, name: str, inst: Optional[str] = None):
        self.name = name
        self.inst = inst
        self.pin = f"{inst}.{name}" if inst else name

    def __repr__(self) -> str:
        return self.pin


###########################################################################
class Net:
    """Represents a net in the schematic."""

    def __init__(self, name: str):
        self.name = name

    def __repr__(self) -> str:
        return self.name


###########################################################################
class Part:
    """Represents a library part declaration."""

    def __init__(self, name: str, pins: List[str]):
        self.name = name
        self.pins = pins
        for p in pins:
            setattr(self, p, Pin(p))

    def __repr__(self) -> str:
        return self.name


###########################################################################
class Component:
    """Represents an instantiated component."""

    def __init__(self, name: str, part: Part):
        self.name = name
        self.part = part
        # clone pins from part to instance name for
        self.pins = part.pins
        for p in self.pins:
            setattr(self, p, Pin(p, name))

    def __repr__(self) -> str:
        return self.name


###########################################################################
class Schematic(BaseSchema):
    '''
    Basic schematic entry class for designing systems with real physical
    components.
    '''

    def __init__(self, name: str = None):
        # in memory object lookup for pythonic access
        # golden truth database is the SC schema
        self.name = name
        self.parts: dict[str, Part] = {}
        self.pins: dict[str, Pin] = {}
        self.nets: dict[str, Net] = {}
        self.components: dict[str, Component] = {}

        # leveraging SC infrastructure as raw dictionary
        super().__init__()
        schema_schematic(self)

    @classmethod
    def _getdict_type(cls):
        return Schematic.__name__

    ######################################################################
    def add_pin(self, name: str, direction: str) -> Pin:
        """
        Add a pin to the schematic object.

        This method creates a new pin in the schematic, storing its name,
        direction, and optional vector bit range in the SC schema.
        If the pin name includes a bus notation (e.g., "data[7:0]"),
        the bit range is automatically extracted.

        Args:
            name (str): The name of the pin. Can include a vector range
                (e.g., "in", "sel", or "data[7:0]").
            direction (str): The pin direction; one of "input", "output", or "inout".

        Returns:
            Pin: The created pin object.
        """

        # handle buses/vectors in names
        m = re.match(r"^([^\[]+)\[(\d+):(\d+)\]$", name)
        bitrange = (0, 0)
        if m:
            name = m.group(1)
            bitrange = (int(m.group(2)), int(m.group(3)))
        # object/string lookup table
        if name in self.pins:
            raise ValueError(f"Pin '{name}' already exists.")
        pin = Pin(name)
        self.pins[name] = pin
        setattr(self, name, pin)
        # store data in SC schema
        self.set('schematic', 'pin', name, 'direction', direction)
        self.set('schematic', 'pin', name, 'bitrange', bitrange)
        return pin

    def get_pindir(self, name: Union[str, Pin]) -> str:
        """
        Get the direction of a named pin.

        Args:
            name (str | Pin): The name of the pin (e.g., "in", "sel")
                or a Pin object with a `name` attribute.

        Returns:
            str: The direction of the pin ("input", "output", or "inout").
        """
        if isinstance(name, Pin):
            name = name.name
        return self.get('schematic', 'pin', name, 'direction')

    def get_pinrange(self, name: Union[str, Pin]) -> Tuple[int, int]:
        """
        Get the vector bit range of a pin.

        Args:
            name (str | Pin): The name of the pin, or a Pin
                object with a `name` attribute.

        Returns:
            tuple[int, int]: The vector bit range of the pin as `(max, min)`.
        """
        if isinstance(name, Pin):
            name = name.name
        return self.get('schematic', 'pin', name, 'bitrange')

    def all_pins(self) -> list[str]:
        """
        Get a list of all pins in the schematic.

        Returns:
            list[str]: A list of pin names defined in the schematic.
        """
        return self.getkeys('schematic', 'pin')

    ##########################################
    def add_net(self, name: str) -> Net:
        """
        Add a named net to the schematic.

        This method creates a new net in the schematic, storing its name
        and vector bit range in the SC schema. If the net name includes a
        bus notation (e.g., "data[7:0]"), the bit range is automatically
        extracted.

        Args:
            name (str): The name of the net. Can include a vector range
                in the form "netname[max:min]" (e.g., "data[7:0]").

        Returns:
            Net: The created net object.
        """
        # handle buses/vectors in names
        m = re.match(r"^([^\[]+)\[(\d+):(\d+)\]$", name)
        bitrange = (0, 0)
        if m:
            name = m.group(1)
            bitrange = (int(m.group(2)), int(m.group(3)))

        # local object lookup
        net = Net(name)
        self.nets[name] = net
        setattr(self, name, net)

        #  store data in SC schema
        self.set('schematic', 'net', name, 'bitrange', bitrange)

        return net

    def get_netrange(self, name: Union[str, Net]) -> Tuple[int, int]:
        """
        Get the vector bit range of a named net.

        Args:
            name (str | Net): The name of the net, or a Net
                object with a `name` attribute.

        Returns:
            tuple[int, int]: The bit range of the net as `(max, min)`.
            For scalar nets, this defaults to `(0, 0)`.
        """

        if isinstance(name, Net):
            name = name.name

        return self.get('schematic', 'net', name, 'bitrange')

    def all_nets(self) -> list[str]:
        """
        Returns list of all schematic nets.
        """
        return self.getkeys('schematic', 'net')

    ####################################################
    def add_part(self, name: str, pins: List[str]) -> Part:
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

        # record pins in SC dictionary
        pins_blasted = []
        for pin in pins:
            m = re.match(r"^([^\[]+)\[(\d+):(\d+)\]$", pin)
            bitrange = (0, 0)
            if m:
                pin = m.group(1)
                bitrange = (int(m.group(2)), int(m.group(3)))
                for i in range(bitrange[1], bitrange[0] + 1):
                    pins_blasted.append(f"{pin}[{i}]")
            else:
                pins_blasted.append(pin)
            # store in SC database
            self.set('schematic', 'part', name, 'pin', pin, 'bitrange', bitrange)

        # local object database
        if name in self.parts:
            raise ValueError(f"Part '{name}' already exists.")
        part = Part(name, pins_blasted)
        self.parts[name] = part
        setattr(self, name, part)

        # return part object
        return part

    def get_partpins(self, part: Part) -> tuple[str]:
        """
        Returns list of part pins
        """

        keys = self.getkeys('schematic', 'part', part.name, 'pin')
        pinlist = []
        for item in keys:
            t = self.get('schematic', 'part', part.name, 'pin', item, 'bitrange')
            if t != (0, 0):
                item = f"{item}[{t[0]}:{t[1]}]"
            pinlist.append(item)
        pins = tuple(pinlist)

        return pins

    #####################################################
    def add_component(self, name: str, part: Part) -> Component:
        """
        Adds component (instance) to the schematic object.

        Args:
            name (str): Instance name
            part (str, obj): Instance partname/cellname.

        Returns:
            str: Pin direction
        """

        # create component
        comp = Component(name, part)
        self.components[name] = comp
        setattr(self, name, comp)

        # SC raw dictionary
        self.set('schematic', 'component', name, 'partname', part.name)

        return comp

    def get_partname(self, inst: Component) -> str:
        """
        Returns part name of named component.

        Args:
           inst (Component): Component object
        Returns:
           Part name (str)
        """

        return self.get('schematic', 'component', inst.name, 'partname')

    def all_components(self) -> list[str]:
        """
        Returns list of all schematic component objects.
        """
        return self.getkeys('schematic', 'component')

    ####################################
    def connect(self, src: Pin, dst: Pin, net: Optional[Net] = None):
        """
        Connect pin to net.

        Args:
            src (Pin): Source pin to connect
            dst (Pin): Destination pin to connect
            net (Net): Net name. Not needed for primary pin.
        """

        if src.inst is None:  # src --> gate
            net = src.name
            self.set('schematic', 'component', dst.inst, 'connection', dst.name, net)
        elif dst.inst is None:  # gate --> dst
            net = dst.name
            self.set('schematic', 'component', src.inst, 'connection', src.name, net)
        elif net is not None:  # gate --> gate
            self.set('schematic', 'component', src.inst, 'connection', src.name, net)
            self.set('schematic', 'component', dst.inst, 'connection', dst.name, net)
        else:
            raise ValueError("Net missing for instance to instance connection.")

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
        port_list = ", ".join(self.all_pins())
        lines.append(f"module {self.name}({port_list});\n")

        # Declare top-level pins
        for pin in self.all_pins():

            direction = self.get('schematic', 'pin', pin, 'direction')
            bits = self.get('schematic', 'pin', pin, 'bitrange')
            if bits[1]:
                bitrange = f"[{bits[1]}:{bits[0]}]"
            else:
                bitrange = ""
            lines.append(f"  {direction} {bitrange} {pin};")

        # Declare nets
        lines.append("\n  // wires\n")
        for net in self.all_nets():
            bits = self.get('schematic', 'net', net, 'bitrange')
            if bits[1]:
                bitrange = f"[{bits[1]}:{bits[0]}]"
            else:
                bitrange = ""
            if net not in self.pins:
                lines.append(f"  wire {bitrange} {net};")

        # Instantiate components
        lines.append("\n  // components\n")
        for inst in self.all_components():
            part = self.get('schematic', 'component', inst, 'partname')
            lines.append(f"  {part} {inst} (")
            port_map = []
            for pin in self.getkeys('schematic', 'part', part, 'pin'):
                bits = self.get('schematic', 'part', part, 'pin', pin, 'bitrange')
                net = self.get('schematic', 'component', inst, 'connection', pin)
                port_map.append(f"    .{pin}({net})")
            lines.append(",\n".join(port_map))
            lines.append("  );\n")

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
    def _resolve_pin(self, pin_obj):
        """
        Resolves and returns the name of a pin from a given object.

        This helper abstracts away differences in pin representations
        so that calling code (e.g., `connect()`) doesn't need to know
        whether pins are stored under `.pin` (new style) or `.name`
        (legacy style).

        Args:
            pin_obj (object): The pin object to resolve. Can be:
                - An object with a `.pin` attribute
                - An object with a `.name` attribute
                - Other types (may return None)

        Returns:
            str or None: The pin name string if found, otherwise None.
        """
        if hasattr(pin_obj, "pin"):
            return pin_obj.pin
        return getattr(pin_obj, "name", None)


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
    pin = 'default'
    net = 'default'
    part = 'default'

    # hierarchy character
    schema.insert(
        'schematic', 'hierchar',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Schematic hierarchy character",
            example=["api: schematic.set('schematic', 'hierchar', '/')"],
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
            example=["api: schematic.set('schematic', 'buschar', '[]')"],
            help=trim("""
            Specifies the character used to express bus bits. If the
            bus character is used as part of a name, it must be
            escaped with a backslash('\').""")))

    # pin direction
    schema.insert(
        'schematic', 'pin', pin, 'direction',
        Parameter(
            '<input,output,inout>',
            scope=Scope.GLOBAL,
            shorthelp="Pin direction",
            example=[
                "api: schematic.set('schematic','pin', 'A', 'direction', 'input')"],
            help=trim("""
            Direction of pin specified on a per pin basis.""")))

    # pin vector size
    schema.insert(
        'schematic', 'pin', pin, 'bitrange',
        Parameter(
            '(int,int)',
            scope=Scope.GLOBAL,
            shorthelp="Pin bitrange",
            example=[
                "api: schematic.set('schematic','pin', 'A', 'bitrange', (7,0)"],
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
                "api: schematic.set('schematic', 'net', 'net0', 'bitrange', (7,0)"],
            help=trim("""
            Net vector bit range specified as (max,min) tuple.""")))

    # part pin vector size ("header")
    schema.insert(
        'schematic', 'part', part, 'pin', pin, 'bitrange',
        Parameter(
            '(int,int)',
            scope=Scope.GLOBAL,
            shorthelp="Library part pin bitrange",
            example=[
                "api: schematic.set('schematic', 'part', 'INV', 'pin', 'A', 'bitrange', (7,0)"],
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
                "api: schematic.set('schematic','component','i0','partname','INV')"],
            help=trim("""
            Partname (cellname) of a component (instance) specified on a
            per instance basis.""")))

    # component connections
    schema.insert(
        'schematic', 'component', inst, 'connection', pin,
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Component pin connections",
            example=[
                "api: schematic.set('schematic','component','i0','connection', 'A[0]', 'in[0]')",
                "api: schematic.set('schematic','component','i0','connection', 'CLK', 'clk_in')"],
            help=trim("""
            Net connections specified on a per instance and per instance-pin basis.
            Pin and net names must include the appropriate bit index in cases of pin or
            net vectors. Bit index optional for scalar nets and pins.""")))
