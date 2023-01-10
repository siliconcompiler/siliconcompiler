
import json

from schema.schema_cfg import scparam

def schema_schematic():
    ''' Schematic configuration
    '''

    cfg = {}

    name = 'default'
    filetype = 'default'

    scparam(cfg,['schematic', 'component', name],
            sctype='str',
            shorthelp="Schematic: component (instance)",
            switch="-schematic_component 'name <str>'",
            example=[
                "cli: -schematic_component 'i0 za001'",
                "api:  chip.set('schematic', 'component', 'i0', 'za001')"],
            schelp="""Unique manufacturer part number (MPN) of the  named
            component.""")

    scparam(cfg, ['schematic', 'net', name],
            sctype='[(str,str)]',
            shorthelp="Schematic: net definition",
            switch="-schematic_net 'name <(str,str)>'",
            example=[
                "cli: -schematic_net 'netA[7:0] (i0,in[7:0])'",
                "api: chip.add('schematic', 'net', 'netA[7:0]', ('i0','in[7:0]'))"],
            schelp="""
            List of component pins and primary design pins connected to the named net
            specified as (component,pin) tuples. For net connnetions to primary
            pins, the 'component' entry should be an empty string. Bused connections
            are specified using the Verilog square bracket syntax (ie [msb:lsb])""")

    scparam(cfg, ['schematic', 'pin', name],
            sctype='(str,str)',
            shorthelp="Schematic: pin definition",
            switch="-schematic_pin 'name <(str,str)>'",
            example=[
                "cli: -schematic_pin 'out[7:0] (output,signal)'",
                "api: chip.set('schematic', 'pin', 'out[7:0]', ('output','signal'))"],
            schelp="""
            Design primary pin definitions, specified (direction,type) tuples
            on a per pin basis. Allowed directions are: input, output, and
            inout. Allowed types are: analog, clock, ground, power, signal.
            An empty 'type' defaults to signal.""")

    scparam(cfg, ['schematic', 'interface', name],
            sctype='[(str,str)]',
            shorthelp="Schematic: interface definition",
            switch="-schematic_interface 'name <(str,str)>'",
            example=[
                "cli: -schematic_interface 'name (clk,clk0)'",
                "api: chip.set('schematic','interface','ddr',('clk','clk0')"],
            schelp="""
            Signal interface definition specified as a list of (key,value) mapping
            tuples, wherein the key is the standardized interface name and the
            value is the design pin name. Bus pins are specified using the Verilog
            square bracket syntax (ie [msb:lsb]).""")

    scparam(cfg, ['schematic', 'parameter', name],
            sctype='[(str,str)]',
            shorthelp="Schematic: parameter definition ",
            switch="-schematic_parameter 'obj <(str,str)>'",
            example=[
                "cli: -schematic_parameter 'i0 (speed,fast)'",
                "api: chip.set('schematic','parameter', 'i0', ('speed','fast')"],
            schelp="""
            List of parameter definitions attached to a named pin, net, or
            component specified as (key,value) tuples.""")

    return cfg

##############################################################################
# Main routine
if __name__ == "__main__":
    cfg = schema_schematic()
    print(json.dumps(cfg, indent=4, sort_keys=True))
