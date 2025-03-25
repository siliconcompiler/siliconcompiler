'''
sv2v converts SystemVerilog (IEEE 1800-2017) to Verilog
(IEEE 1364-2005), with an emphasis on supporting synthesizable
language constructs. The primary goal of this project is to
create a completely free and open-source tool for converting
SystemVerilog to Verilog. While methods for performing this
conversion already exist, they generally either rely on
commercial tools, or are limited in scope.

Documentation: https://github.com/zachjs/sv2v

Sources: https://github.com/zachjs/sv2v

Installation: https://github.com/zachjs/sv2v
'''


####################################################################
# Make Docs
####################################################################
def make_docs(chip):
    from siliconcompiler.tools.sv2v import convert
    convert.setup(chip)
    return chip


def parse_version(stdout):
    # 0.0.7-130-g1aa30ea
    stdout = stdout.strip()
    if '-' in stdout:
        return '-'.join(stdout.split('-')[:-1])
    return stdout


##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("sv2v.json")
