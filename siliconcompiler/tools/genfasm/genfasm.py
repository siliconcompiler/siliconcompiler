'''
Generate a `FSAM <https://github.com/chipsalliance/fasm>`_ file from the output of
`VPR <https://github.com/verilog-to-routing/vtr-verilog-to-routing>`_

Documentation: https://docs.verilogtorouting.org/en/latest/utils/fasm/

Sources: https://github.com/verilog-to-routing/vtr-verilog-to-routing/tree/master/utils/fasm
'''

from siliconcompiler.tools.vpr import vpr


######################################################################
# Make Docs
######################################################################
def make_docs(chip):
    from tools.genfasm.bitstream import setup
    setup(chip)
    return chip


def runtime_options(chip):

    # ***NOTE:  genfasm requires that you match VPR's command line
    #           exactly; so replicate that here
    return vpr.runtime_options(chip, tool='genfasm')


##################################################
if __name__ == "__main__":
    chip = make_docs()
    chip.write_manifest("genfasm.json")
