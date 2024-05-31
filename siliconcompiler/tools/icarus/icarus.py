
'''
Icarus is a verilog simulator with full support for Verilog
IEEE-1364. Icarus can simulate synthesizable as well as
behavioral Verilog.

Documentation: https://steveicarus.github.io/iverilog/

Sources: https://github.com/steveicarus/iverilog

Installation: https://github.com/steveicarus/iverilog
'''


####################################################################
# Make Docs
####################################################################
def make_docs(chip):
    from siliconcompiler.tools.icarus.compile import setup
    setup(chip)
    return chip


################################
# Version Check
################################
def parse_version(stdout):
    # First line: Icarus Verilog version 10.1 (stable) ()
    return stdout.split()[3]


##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("icarus.json")
