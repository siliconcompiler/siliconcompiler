'''
Chisel is a hardware design language that facilitates advanced circuit
generation and design reuse for both ASIC and FPGA digital logic designs.
Chisel adds hardware construction primitives to the Scala programming
language, providing designers with the power of a modern programming
language to write complex, parameterizable circuit generators that produce
synthesizable Verilog.

Documentation: https://www.chisel-lang.org/docs

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
