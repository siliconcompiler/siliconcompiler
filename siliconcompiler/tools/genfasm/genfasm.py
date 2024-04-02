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
    from tools.genfasm.bitstream import setup
    setup(chip)
    return chip


##################################################
if __name__ == "__main__":
    chip = make_docs()
    chip.write_manifest("genfasm.json")
