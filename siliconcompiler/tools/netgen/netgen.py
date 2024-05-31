
'''
Netgen is a tool for comparing netlists. By comparing a Verilog netlist with
one extracted from a circuit layout, it can be used to perform LVS
verification.

Documentation: http://www.opencircuitdesign.com/netgen/

Installation: https://github.com/RTimothyEdwards/netgen

Sources: https://github.com/RTimothyEdwards/netgen
'''


####################################################################
# Make Docs
####################################################################
def make_docs(chip):
    from siliconcompiler.tools.netgen.lvs import setup
    setup(chip)
    return chip


################################
# Version Check
################################
def parse_version(stdout):
    # First line: Netgen 1.5.190 compiled on Fri Jun 25 16:05:36 EDT 2021
    return stdout.split()[1]


##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("netgen.json")
