import os
import subprocess
import re

import siliconcompiler

####################################################################
# Make Docs
####################################################################

def make_docs():
    '''
    Verilator is a free and open-source software tool which converts Verilog (a
    hardware description language) to a cycle-accurate behavioral model in C++
    or SystemC.

    Steps supported
    ---------------

    **import**

    Preprocesses and pickles Verilog sources. Takes in a set of Verilog source
    files supplied via :keypath:`input, verilog` and reads the following
    parameters:

    * :keypath:`option, ydir`
    * :keypath:`option, vlib`
    * :keypath:`option, idir`
    * :keypath:`option, cmdfile`

    Outputs a single Verilog file in ``outputs/<design>.v``.

    **lint**

    Lints Verilog source. Takes in a single pickled Verilog file from
    ``inputs/<design>.v`` and produces no outputs. Results of linting can be
    programatically queried using errors/warnings metrics.

    **compile**

    Compiles Verilog and C/C++ sources into an executable.  Takes in a single
    pickled Verilog file from ``inputs/<design>.v`` and a set of C/C++ sources
    from :keypath:`input, c`. Outputs an executable in
    ``outputs/<design>.vexe``.

    This steps accepts a restricted set of CLI switches in :keypath:`tool,
    verilator, var, <step>, <index>, extraopts` that are passed through
    directly to Verilator. Currently supported switches include:

    * ``--trace``


    For all steps, this driver runs Verilator using the ``-sv`` switch to enable
    parsing a subset of SystemVerilog features. All steps also support using
    :keypath:`option, relax` to make warnings nonfatal.

    Documentation: https://verilator.org/guide/latest

    Sources: https://github.com/verilator/verilator

    Installation: https://verilator.org/guide/latest/install.html

    '''

    chip = siliconcompiler.Chip('<design>')
    chip.set('arg','step','import')
    chip.set('arg','index','<index>')
    setup(chip)
    return chip

################################
# Setup Tool (pre executable)
################################

def setup(chip):
    ''' Per tool function that returns a dynamic options string based on
    the dictionary settings. Static setings only.
    '''
    tool = 'verilator'
    step = chip.get('arg','step')
    index = chip.get('arg','index')
    design = chip.get_entrypoint()

    # Standard Setup
    chip.set('tool', tool, 'exe', 'verilator')
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=4.028', clobber=False)
    chip.set('tool', tool, 'threads', step, index,  os.cpu_count(), clobber=False)

    # Basic warning and error grep check on logfile
    chip.set('tool', tool, 'regex', step, index, 'warnings', r"^\%Warning", clobber=False)
    chip.set('tool', tool, 'regex', step, index, 'errors', r"^\%Error", clobber=False)

    if step not in ('import', 'lint', 'compile'):
        # If not using one of the pre-packaged steps, return early
        # TODO: should we do this or error out? This allows the user to drive
        # Verilator by filling in the tool options outside this driver.
        return

    # Generic CLI options (for all steps)
    chip.set('tool', tool, 'option', step, index,  '-sv')
    chip.add('tool', tool, 'option', step, index, f'--top-module {design}')

    if chip.get('option', 'relax'):
        # Make warnings non-fatal in relaxed mode
        chip.add('tool', tool, 'option', step, index, ['-Wno-fatal', '-Wno-UNOPTFLAT'])

    # Step-based CLI options
    if step == 'import':
        chip.add('tool', tool, 'option', step, index,  ['--lint-only', '--debug'])
        for value in chip.get('option', 'define'):
            chip.add('tool', tool, 'option', step, index, '-D' + value)
        # File-based arguments added in runtime_options()
    elif step == 'lint':
        chip.add('tool', tool, 'option', step, index,  ['--lint-only', '--debug'])
        chip.add('tool', tool, 'option', step, index, f'inputs/{design}.v')
    elif step == 'compile':
        chip.add('tool', tool, 'option', step, index,  ['--cc', '--exe'])
        chip.add('tool', tool, 'option', step, index, f'inputs/{design}.v')
        chip.add('tool', tool, 'option', step, index, f'-o ../outputs/{design}.vexe')

        if chip.valid('tool', tool, 'var', step, index, 'extraopts'):
            extra_opts = chip.get('tool', tool, 'var', step, index, 'extraopts')
            for opt in extra_opts:
                if opt not in ('--trace'):
                    chip.error(f'Illegal option {opt}')
                chip.add('tool', tool, 'option', step, index, opt)
        # File-based arguments added in runtime_options()

   # I/O requirements
    if step == 'import':
        chip.add('tool', tool, 'require', step, index, ",".join(['input', 'verilog']))
        chip.set('tool', tool, 'output', step, index, f'{design}.v')
    elif step == 'lint':
        chip.set('tool', tool, 'input', step, index, f'{design}.v')
    elif step == 'compile':
        chip.add('tool', tool, 'require', step, index, ",".join(['input', 'c']))
        chip.set('tool', tool, 'input', step, index, f'{design}.v')
        chip.set('tool', tool, 'output', step, index, f'{design}.vexe')

################################
#  Custom runtime options
################################

def runtime_options(chip):
    '''
    CLI options that involve filepaths (must be resolved at runtime, in case
    we're running on a different machine than client).
    '''
    cmdlist = []
    step = chip.get('arg', 'step')

    if step == 'import':
        for value in chip.find_files('option', 'ydir'):
            cmdlist.append('-y ' + value)
        for value in chip.find_files('option', 'vlib'):
            cmdlist.append('-v ' + value)
        for value in chip.find_files('option', 'idir'):
            cmdlist.append('-I' + value)
        for value in chip.find_files('option', 'cmdfile'):
            cmdlist.append('-f ' + value)
        for value in chip.find_files('input', 'verilog'):
            cmdlist.append(value)
    elif step == 'compile':
        for value in chip.find_files('input', 'c'):
            cmdlist.append(value)

    return cmdlist

################################
# Version Check
################################

def parse_version(stdout):
    # Verilator 4.104 2020-11-14 rev v4.104
    return stdout.split()[1]

################################
# Post_process (post executable)
################################

def post_process(chip):
    ''' Tool specific function to run after step execution
    '''

    design = chip.get_entrypoint()
    step = chip.get('arg','step')

    if step == 'import':
        # Post-process hack to collect vpp files
        # Creating single file "pickle' synthesis handoff
        subprocess.run('egrep -h -v "\\`begin_keywords" obj_dir/*.vpp > verilator.v',
                       shell=True)

        # Moving pickled file to outputs
        os.rename("verilator.v", f"outputs/{design}.v")
    elif step == 'compile':
        # Run make to compile Verilated design into executable.
        # If we upgrade our minimum supported Verilog, we can remove this and
        # use the --build flag instead.
        subprocess.run(['make', '-C', 'obj_dir', '-f', f'V{design}.mk'])

##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("verilator.json")
