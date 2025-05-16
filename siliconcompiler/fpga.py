from siliconcompiler.schema import BaseSchema
from siliconcompiler.schema import EditableSchema, Parameter, Scope
from siliconcompiler.schema.utils import trim


class FPGASchema(BaseSchema):
    def __init__(self):
        super().__init__()

        schema_fpga(self)


###############################################################################
# FPGA
###############################################################################
def schema_fpga(schema):
    schema = EditableSchema(schema)

    partname = 'default'
    key = 'default'

    schema.insert(
        'partname',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="FPGA: part name",
            switch="-fpga_partname <str>",
            example=["cli: -fpga_partname fpga64k",
                     "api: chip.set('fpga', 'partname', 'fpga64k')"],
            help=trim("""
            Complete part name used as a device target by the FPGA compilation
            tool. The part name must be an exact string match to the partname
            hard coded within the FPGA EDA tool.""")))

    schema.insert(
        partname, 'vendor',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="FPGA: vendor name",
            switch="-fpga_vendor 'partname <str>'",
            example=["cli: -fpga_vendor 'fpga64k acme'",
                     "api: chip.set('fpga', 'fpga64k', 'vendor', 'acme')"],
            help=trim("""
            Name of the FPGA vendor for the FPGA partname.""")))

    schema.insert(
        partname, 'lutsize',
        Parameter(
            'int',
            scope=Scope.GLOBAL,
            shorthelp="FPGA: lutsize",
            switch="-fpga_lutsize 'partname <int>'",
            example=["cli: -fpga_lutsize 'fpga64k 4'",
                     "api: chip.set('fpga', 'fpga64k', 'lutsize', '4')"],
            help=trim("""
            Specify the number of inputs in each lookup table (LUT) for the
            FPGA partname.  For architectures with fracturable LUTs, this is
            the number of inputs of the unfractured LUT.""")))

    schema.insert(
        partname, 'file', key,
        Parameter(
            '[file]',
            scope=Scope.GLOBAL,
            shorthelp="FPGA: file",
            switch="-fpga_file 'partname key <file>'",
            example=["cli: -fpga_file 'fpga64k archfile my_arch.xml'",
                     "api: chip.set('fpga', 'fpga64k', 'file', 'archfile', 'my_arch.xml')"],
            help=trim("""
            Specify a file for the FPGA partname.""")))

    schema.insert(
        partname, 'var', key,
        Parameter(
            '[str]',
            scope=Scope.GLOBAL,
            shorthelp="FPGA: var",
            switch="-fpga_var 'partname key <str>'",
            example=["cli: -fpga_var 'fpga64k channelwidth 100'",
                     "api: chip.set('fpga', 'fpga64k', 'var', 'channelwidth', '100')"],
            help=trim("""
            Specify a variable value for the FPGA partname.""")))
