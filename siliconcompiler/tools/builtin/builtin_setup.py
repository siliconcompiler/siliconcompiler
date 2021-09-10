import os
import subprocess
import re
import sys
import siliconcompiler
import shutil

def setup_tool(chip, step, index):
    '''
    NOP
    '''

def pre_process(chip, step, index):
    '''
    Using pre-process for built in functions
    '''

    function = chip.get('flowgraph', step, index, 'function')
    arglist = chip.get('flowgraph', step, index, 'args')
    input_step = chip.getkeys('flowgraph', step, index, 'input')[0]

    # Functions that filter down index functions
    if function in ('maximum', 'minimum'):
        input_step = chip.getkeys('flowgraph', step, index, 'input')[0]
        if function == 'minimum':
            selindex = chip.minimum(input_step)
        else:
            selindex = chip.maximum(input_step)
        # recording winner in schema
        self.set('flowstatus', input_step, 'select', sel_index, clobber=True)
        self.logger.info(f"Step '{step}' selected index '{sel_index}' from '{input_step}'.")
        # copy files
        shutil.copytree(f"../{input_step}{sel_index}/outputs", 'inputs/')
    # Functions that work on multiple steps (index=0)
    elif function == "merge":
        for input_step in self.getkeys('flowgraph', step, index, 'input'):
            #TODO: Fix conclicts
            shutil.copytree(f"../{input_step}0/outputs", 'inputs/')
    elif function == "mux":
        for input_step in self.getkeys('flowgraph', step, index, 'input'):
            #TODO: Fix conclicts
            shutil.copytree(f"../{input_step}0/outputs", 'inputs/')


        for input_step in self.getkeys('flowgraph', step, index, 'input'):
            if self.get('flowgraph', step, index, 'input', input_step):
                min_index = self.minimum(input_step)
                self.logger.info(f"Step '{step}' selected index '{min_index}' from '{input_step}'.")
                self.set('flowstatus', input_step, 'select', str(min_index), clobber=True)
                # copy files
                shutil.copytree(f"../{input_step}{min_index}/outputs", 'inputs/')


def post_process(chip, step, index):
    ''' Tool specific function to run after step execution
    '''

    # Creating single file "pickle' synthesis handoff
    subprocess.run('egrep -h -v "\\`begin_keywords" obj_dir/*.vpp > verilator.v',
                   shell=True)

    # setting top module of design
    modules = 0
    if len(chip.cfg['design']['value']) < 1:
        with open("verilator.v", "r") as open_file:
            for line in open_file:
                modmatch = re.match(r'^module\s+(\w+)', line)
                if modmatch:
                    modules = modules + 1
                    topmodule = modmatch.group(1)
        # Only setting design when possible
        if (modules > 1) & (chip.cfg['design']['value'] == ""):
            chip.logger.error('Multiple modules found during import, \
            but sc_design was not set')
            sys.exit()
        else:
            chip.logger.info('Setting design (topmodule) to %s', topmodule)
            chip.cfg['design']['value'].append(topmodule)
    else:
        topmodule = chip.cfg['design']['value']

    # Copy files from inputs to outputs
    shutil.copytree("inputs", "outputs", dirs_exist_ok=True)

    # Moving pickled file to outputs
    os.rename("verilator.v", "outputs/" + topmodule + ".v")

    # Clean up
    shutil.rmtree('obj_dir')

    #Return 0 if successful
    return 0

##################################################
if __name__ == "__main__":

    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'

    # create a chip instance
    chip = siliconcompiler.Chip()
    # load configuration
    setup_tool(chip, step='import', index='0')
    # write out results
    chip.writecfg(output)
