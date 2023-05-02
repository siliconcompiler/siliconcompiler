'''
Chisel is a hardware design language that facilitates advanced circuit
generation and design reuse for both ASIC and FPGA digital logic designs.
Chisel adds hardware construction primitives to the Scala programming
language, providing designers with the power of a modern programming
language to write complex, parameterizable circuit generators that produce
synthesizable Verilog.

Documentation: https://www.chisel-lang.org/chisel3/docs/introduction.html

Sources: https://github.com/chipsalliance/chisel

Installation: The Chisel plugin relies on having the Scala Build Tool (sbt)
installed. Instructions: https://www.scala-sbt.org/download.html.
'''

from siliconcompiler.tools.chisel import convert


####################################################################
# Make Docs
####################################################################
def make_docs(chip):
    convert.setup(chip)
    return chip


def parse_version(stdout):
    # sbt version in this project: 1.5.5
    # sbt script version: 1.5.5

    for line in stdout.splitlines():
        line = line.strip()
        if 'sbt script version:' in line:
            return line.split()[-1]

    return None


################################
#  Custom runtime options
################################
def runtime_options(chip):

    cmdlist = []

    # TODO: handle these parameters

    # for value in chip.find_files('ydir'):
    #     cmdlist.append('-y ' + value)
    # for value in chip.find_files('vlib'):
    #     cmdlist.append('-v ' + value)
    # for value in chip.find_files('idir'):
    #     cmdlist.append('-I' + value)
    # for value in chip.get('define'):
    #     cmdlist.append('-D' + value)
    # for value in chip.find_files('cmdfile'):
    #     cmdlist.append('-f ' + value)

    # # Set up user-provided parameters to ensure we elaborate the correct modules
    # for param in chip.getkeys('param'):
    #     value = chip.get('param', param)
    #     cmdlist.append(f'-P{param}={value}')

    return cmdlist
