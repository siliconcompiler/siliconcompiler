from typing import List, Union

from siliconcompiler.schema import NamedSchema
from siliconcompiler.schema import EditableSchema, Parameter, Scope
from siliconcompiler.schema.utils import trim


###########################################################################
class SchematicSchema(NamedSchema):
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
        super().__init__()
        self.set_name(name)
        self.index = 0

        schema_schematic(self)

    ######################################################################
    def add_pin(self, name: str, pindir: str, bitrange=(0,0)):
        """
        Adds pin to schematic object.

        Args:
            name (str):
                Pin name (e.g., "in", "sel", out", "A", "Z").

            pindir (str):
                Pin direction (input, output, or inout).

            bitrange (int,int):
                Vector Range (max, min).

        """

        self.set('schematic', 'pin', name, 'direction', pindir)
        self.set('schematic', 'pin', name, 'bitrange', bitrange)

    def get_pindir(self, name: str):
        """
        Returns direction of named pin.

        Args:
            name (str):
                Pin name (e.g., "in", "sel", out", "A", "Z").

        Returns:
            str: Pin direction

        """
        return self.get('schematic', 'pin', name, 'direction')

    def get_pinrange(self, name: str):
        """
        Returns vector bit range of named pin.

        Args:
            name (str):
                Pin name (e.g., "in", "sel", out", "A", "Z").

        Returns:
            str: Pin vector bit range

        """
        return self.get('schematic', 'pin', name, 'bitrange')

    def all_pins(self):
        """
        Returns list of all schematic pins.

        Returns:
           list[str]: List of pins

        """
        return self.getkeys('schematic', 'pin')

    ######################################################################
    def add_component(self, instance: str, part: str):
        """
        Adds component to the schematic object.

        Args:
            instance (str):
                Instance name (e.g., "i0", "inst0", "myCell").

            part (str):
                Component partname/cellname. (eg. "NAND2X1")

        Returns:
            str: Pin direction

        """

        return self.set('schematic', 'component', instance, 'partname', part)

    def get_partname(self, inst: str):
        """
        Returns instance part name.

        Args:
            inst (str):
                Instance name (e.g., "i0", "inst0", "myCell").

        Returns:
           list[str]: Instance part name

        """

        return self.get('schematic', 'component', inst, 'partname')

    def all_components(self):
        """
        Returns list of all schematic components.

        Returns:
           list[str]: List of components

        """

        return self.getkeys('schematic', 'component')

    ######################################################################
    def connect_net(self,
                    pins: Union[List[str], str],
                    netname: str = None) -> List[str]:
        """
        Connect one or more schematic pins to a net name.

        Component connections specified as "inst.pinname" and primary
        design pins specified as "pinname".

        If no net name is entered, a netname is automatically generated based
        on the order that the connect function is called. The automatically
        generated net names are "net0, net1, net2, ..etc).

        Args:
            pins (str or List[str]):
                 List of pins to connect.

            netname (str, optional):
                 Net name

        Returns:
            str: List of pins connected to net

        """

        if netname is None:
            netname = f"net{self.index}"
            self.index = self.index + 1

        return self.add('schematic', 'net', netname, 'connection', pins)

    def get_net(self, netname: str = None) -> List[str]:
        """
        Return list of pins connected to net.

        Args:

            netname (str, optional):
                 Net name

        Returns:
            str: List of pins connected to net

        """

        return self.get('schematic', 'net', netname, 'connection')

    ######################################################################
    def write_json(self,filename):
       """
        Writes out schematic as a JSON netlist.

        Args:
            filename (str or Path):
                Path to the output netlist file.

        """



    ######################################################################
    def write_verilog(self, filename):
        """
        Writes out schematic as a Verilog netlist.

        Args:
            filename (str or Path):
                Path to the output netlist file.

        """

        if filename is None:
            raise ValueError("filename cannot be None")

        # Module definition
        module_name = self.get_name()

        # Port definitiosn (collect bits as buses)
        port_lines = []

        # Wire definitions (collect bits as buses)
        wire_lines = []

        # Instances (collect bits as buses)
        inst_lines = []

        # Write Verilog
        with open(filename, "w") as f:

            # Module
            all_ports = []
            f.write(f"module {module_name}({', '.join(all_ports)});\n\n")

            # Port declaration
            for line in port_lines:
                f.write(line + "\n")
            f.write("\n")

            # Wire declarations
            for line in wire_lines:
                f.write(line + "\n")
            f.write("\n")

            # Instances
            for line in inst_lines:
                f.write(line + "\n")

            # Endmodule
            f.write("\nendmodule\n")

###########################################################################
# Helper Functions
###########################################################################

def _get_netlist(self):
    '''
    Walks schematic schema and returns a clean netlist.
    '''
    netlist = {}
    netlist["module"] = self.get_name()

    # pins
    netlist["pins"] = {}
    for item in self.all_pins():
        netlist["pins"][item] = {}
        bitrange = self.get('schematic', 'pin', item, 'bitrange')
        netlist["pins"][item]["bitrange"] = bitrange

    # nets
    netlist["nets"] = {}
    for item in self.all_nets():
        netlist["nets"][item] = {}
        bitrange = self.get('schematic', 'net', item, 'bitrange')
        netlist["nets"][item]["bitrange"] = bitrange

    # components
    netlist["cells"] = {}
    for inst in self.all_components():
        netlist["components"][inst] = {}
        # partname
        partname = self.get('schematic', 'component', inst, 'partname')
        netlist["components"][inst]["partname"] = partname
        # connections
        netlist["components"][inst]["connection"] = {}
        all_pins = self.getkeys('schematic', 'component', inst, 'connection')
        for pin in all_pins:
            conn = self.get('schematic', 'component', inst, 'connection', pin)
            netlist["components"][inst]["connection"][pin] = conn

    return netlist

###########################################################################
# Schema
###########################################################################
def schema_schematic(schema):
    '''
    Defines the schema parameters specific to a schematic.

    This function is called by the `SchematicSchema` constructor to set up
    all schematic parameters:

    Args:
        schema (SchematicSchema): The schema object to configure.
    '''

    schema = EditableSchema(schema)

    inst = 'default'
    pin = 'default'
    net = 'default'

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
        'schematic', 'pin', pin, 'direction',
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
        'schematic', 'pin', pin, 'bitrange',
        Parameter(
            '(int,int)',
            scope=Scope.GLOBAL,
            shorthelp="Pin bitrange",
            example=[
                "api: chip.set('schematic','pin', 'A', 'bitrange', (7,0)"],
            help=trim("""
            Pin vector size, specified as a (max,min) tuple. A range of (0,0)
            indicates a scalar single bit pin.""")))

    # cell partname
    schema.insert(
        'schematic', 'component', inst, 'partname',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Component part name",
            example=[
                "api: chip.set('schematic','component','i0','partname','INV')"],
            help=trim("""
            Component partname/cellname specified on a per instance basis.""")))


    # cell connections
    schema.insert(
        'schematic', 'component', inst, 'connection', pin,
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
            Net vector bit range specieid as a (max,min) tuple.""")))
