
'''
GHDL is an open-source analyzer, compiler, simulator and
(experimental) synthesizer for VHDL. It allows you to analyse
and elaborate sources for generating machine code from your design.
Native program execution is the only way for high speed simulation.

Documentation: https://ghdl.readthedocs.io/en/latest

Sources: https://github.com/ghdl/ghdl

Installation: https://github.com/ghdl/ghdl
'''


#####################################################################
# Make Docs
#####################################################################
def make_docs(chip):
    from siliconcompiler.tools.ghdl import convert
    convert.setup(chip)
    return chip


################################
# Version Check
################################
def parse_version(stdout):
    # first line: GHDL 2.0.0-dev (1.0.0.r827.ge49cb7b9) [Dunoon edition]

    # '*-dev' is interpreted by packaging.version as a "developmental release",
    # which has the correct semantics. e.g. Version('2.0.0') > Version('2.0.0-dev')
    return stdout.split()[1]


##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("ghdl.json")
