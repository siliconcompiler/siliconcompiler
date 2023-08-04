import os
import re

from siliconcompiler.tools.surelog.surelog import setup as setup_tool


##################################################
def setup(chip):
    '''
    Import verilog files
    '''

    # Generic tool setup.
    setup_tool(chip)

    tool = 'surelog'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    # Runtime parameters.
    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             step=step, index=index, clobber=False)

    # Command-line options.
    options = []
    # -parse is slow but ensures the SV code is valid
    # we might want an option to control when to enable this
    # or replace surelog with a SV linter for the validate step
    options.append('-parse')
    # We don't use UHDM currently, so disable. For large designs, this file is
    # very big and takes a while to write out.
    options.append('-nouhdm')
    # Write back options to cfg
    chip.add('tool', tool, 'task', task, 'option', options, step=step, index=index)

    # Input/Output requirements
    chip.add('tool', tool, 'task', task, 'output', chip.top() + '.v', step=step, index=index)

    # Schema requirements
    chip.add('tool', tool, 'task', task, 'require', ",".join(['input', 'rtl', 'verilog']),
             step=step, index=index)


##################################################
def post_process(chip):
    ''' Tool specific function to run after step execution
    '''

    # https://github.com/chipsalliance/Surelog/issues/3776#issuecomment-1652465581
    surelog_escape = re.compile(r"#~@([a-zA-Z_0-9.\$/\:\[\] ]*)#~@")

    # Look in slpp_all/file_elab.lst for list of Verilog files included in
    # design, read these and concatenate them into one pickled output file.
    with open('slpp_all/file_elab.lst', 'r') as filelist, \
            open(f'outputs/{chip.top()}.v', 'w') as outfile:
        for path in filelist.read().split('\n'):
            path = path.strip('"')
            if not path:
                # skip empty lines
                continue
            with open(path, 'r') as infile:
                infile_data = infile.read()
                unescaped_data = surelog_escape.sub(r"\\\1 ", infile_data)
                outfile.write(unescaped_data)
                if not unescaped_data.endswith('\n'):
                    # in case end of file is missing a newline
                    outfile.write('\n')
