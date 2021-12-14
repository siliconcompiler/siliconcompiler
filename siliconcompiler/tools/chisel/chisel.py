import os

import siliconcompiler

####################################################################
# Make Docs
####################################################################
def make_docs():
    '''
    Chisel is a hardware design language that facilitates advanced circuit
    generation and design reuse for both ASIC and FPGA digital logic designs.
    Chisel adds hardware construction primitives to the Scala programming
    language, providing designers with the power of a modern programming
    language to write complex, parameterizable circuit generators that produce
    synthesizable Verilog.

    Documentation: https://www.chisel-lang.org/chisel3/docs/introduction.html

    Sources: https://github.com/chipsalliance/chisel3

    Installation: The Chisel plugin relies on having the Scala Build Tool (sbt)
    installed. Instructions: https://www.scala-sbt.org/download.html.
    '''

    chip = siliconcompiler.Chip()
    chip.set('arg','step','import')
    chip.set('arg','index','0')
    chip.set('design', '<design>')
    setup_tool(chip)
    return chip

################################
# Setup Tool (pre executable)
################################

def setup_tool(chip):
    ''' Sets up default settings on a per step basis
    '''

    tool = 'chisel'
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    # Standard Setup
    refdir = 'tools/'+tool
    chip.set('eda', tool, step, index, 'exe', 'sbt', clobber=False)
    chip.set('eda', tool, step, index, 'refdir', refdir, clobber=False)
    chip.set('eda', tool, step, index, 'vswitch', '--version', clobber=False)
    chip.set('eda', tool, step, index, 'version', '1.5.5', clobber=False)
    chip.set('eda', tool, step, index, 'threads', os.cpu_count(), clobber=False)
    chip.set('eda', tool, step, index, 'copy', True, clobber=False)

    design = chip.get('design')
    option = f'"runMain SCDriver --module {design} -o ../outputs/{design}.v"'
    chip.set('eda', tool, step, index, 'option', option)

    # Input/Output requirements
    chip.add('eda', tool, step, index, 'output', chip.get('design') + '.v')

def parse_version(stdout):
    # sbt version in this project: 1.5.5
    # sbt script version: 1.5.5

    # grab version # by splitting on whitespace
    return stdout.split('\n')[0].split()[-1]

################################
#  Custom runtime options
################################

def runtime_options(chip):

    cmdlist = []

    # TODO: handle these flags

    # # source files
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
    # for value in chip.find_files('source'):
    #     cmdlist.append(value)

    # cmdlist.append('-top ' + chip.get('design'))
    # # make sure we can find .sv files in ydirs
    # cmdlist.append('+libext+.sv')

    # # Set up user-provided parameters to ensure we elaborate the correct modules
    # for param in chip.getkeys('param'):
    #     value = chip.get('param', param)
    #     cmdlist.append(f'-P{param}={value}')

    return cmdlist

################################
# Post_process (post executable)
################################

def post_process(chip):
    ''' Tool specific function to run after step execution
    '''
    return 0
