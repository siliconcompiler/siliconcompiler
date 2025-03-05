from siliconcompiler.tools.vpr.vpr import parse_version as vpr_parse_version
from siliconcompiler.tools.vpr.vpr import normalize_version as vpr_normalize_version
from siliconcompiler.tools.vpr.vpr import add_tool_requirements as add_vpr_requirements

'''
Generate a `FSAM <https://github.com/chipsalliance/fasm>`_ file from the output of
`VPR <https://github.com/verilog-to-routing/vtr-verilog-to-routing>`_

Documentation: https://docs.verilogtorouting.org/en/latest/utils/fasm/

Sources: https://github.com/verilog-to-routing/vtr-verilog-to-routing/tree/master/utils/fasm
'''


######################################################################
# Make Docs
######################################################################
def make_docs(chip):
    from siliconcompiler.tools.genfasm.bitstream import setup
    setup(chip)
    return chip


def setup(chip):
    chip.set('tool', 'genfasm', 'exe', 'genfasm', clobber=False)
    chip.set('tool', 'genfasm', 'vswitch', '--version')
    chip.set('tool', 'genfasm', 'version', '>=9.0.0', clobber=False)

    add_tool_requirements(chip)


def add_tool_requirements(chip):
    add_vpr_requirements(chip)


def parse_version(chip):
    return vpr_parse_version(chip)


def normalize_version(chip):
    return vpr_normalize_version(chip)


##################################################
if __name__ == "__main__":
    chip = make_docs()
    chip.write_manifest("genfasm.json")
