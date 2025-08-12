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
    def add_pin(self, name: str, pindir: str):
        """
        Adds pin to schematic object.

        Args:
            name (str):
                Pin name (e.g., "in", "sel", out", "A", "Z").

            pindir (str):
                Pin direction (input, output, or inout).

        Returns:
            str: Pin direction

        """

        return self.set('schematic', 'pin', name, 'dir', pindir)

    def get_pindir(self, name: str):
        """
        Returns direction of named pin.

        Args:
            name (str):
                Pin name (e.g., "in", "sel", out", "A", "Z").

        Returns:
            str: Pin direction

        """
        return self.getkeys('schematic', 'pin', name, 'direction')

    def all_pins(self):
        """
        Returns list of all schematic pins.

        Returns:
           list[str]: List of pins

        """
        return self.getkeys('schematic', 'pin')

    ######################################################################
    def add_component(self, inst: str, part: str):
        """
        Adds component to the schematic object.

        Args:
            inst (str):
                Instance name (e.g., "i0", "inst0", "myCell").

            part (str):
                Component partname/cellname. (eg. "NAND2X1")

        Returns:
            str: Pin direction

        """

        return self.set('schematic', 'component', inst, 'partname', part)

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
    def connect(self,
                pins: Union[List[str], str],
                netname: str = None) -> List[str]:
        """
        Connect one or more schematic pins to a net name.

        If no netname is entered, a netname is automatically generated based
        on the order that the connect function is called. The automatically
        generated net names are "net0, net1, net2,..etc).

        Args:
            pins (str or List[str]):
                 List of pins to connect.

            netname (str, optional):
                 Net name

        Returns:
            str: Pin direction

        """

        if netname is None:
            netname = f"net{self.index}"
            self.index = self.index + 1

        return self.add('schematic', 'net', netname, 'connection', pins)


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

    name = 'default'

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

    # partname
    schema.insert(
        'schematic', 'component', name, 'partname',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Component part name",
            example=[
                "api: chip.set('schematic','component','i0','partname','INV')"],
            help=trim("""
            Component partname/cellname specified on a per instance basis.""")))

    # pin definitions
    schema.insert(
        'schematic', 'pin', name, 'direction',
        Parameter(
            '<input,output,inout>',
            scope=Scope.GLOBAL,
            shorthelp="Pin direction",
            example=[
                "api: chip.set('schematic','pin', 'A', 'direction', 'input')"],
            help=trim("""
            Direction of pin specified on a per pin basis.""")))

    # net connections
    schema.insert(
        'schematic', 'net', name, 'connection',
        Parameter(
            '[str]',
            scope=Scope.GLOBAL,
            shorthelp="Net connections",
            example=[
                "api: chip.set('schematic','net','net0','connect','I42.Z')"],
            help=trim("""
            Net connections specified as a list of connection points on a
            per net basis. The connection point point format is "INSTANCE.PIN",
            where "." is the hierarchy character. Connections without ".PIN"
            implies the connection is a primary design I/O pin. Specifying
            "INSTANCE.*" implies that all pins of INSTANCE get connected to
            the net.""")))
