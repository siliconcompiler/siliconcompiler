import os
import re
import sys
import defusedxml.ElementTree as ET
from siliconcompiler.schema import schema_path

def setup_tool(chip, step):
     chip.logger.debug("Setting up Yosys")     
     
     refdir = 'eda/yosys'

     chip.add('flow', step, 'format', 'tcl')
     chip.add('flow', step, 'copy', 'true')
     chip.add('flow', step, 'vendor', 'yosys')
     chip.add('flow', step, 'exe', 'yosys')
     chip.add('flow', step, 'option', '-c')
     chip.add('flow', step, 'refdir', refdir)
     chip.add('flow', step, 'script', refdir + '/sc_syn.tcl')
   
def setup_options(chip, step):

     options = chip.get('flow', step, 'option')
     return options

################################
# Pre and Post Run Commands
################################
def pre_process(chip, step):
    ''' Tool specific function to run before step execution
    '''

    targetlist = chip.get('target')[-1].split('_')
    if targetlist[0] == 'openfpga':
        # Synthesis for OpenFPGA/VPR needs to know the size of the LUTs in the
        # FPGA architecture. We infer this from the VPR architecture file, then
        # dump it to a TCL file imported by the synthesis script.
        # Inference code adapted from OpenFPGA:
        # https://github.com/lnis-uofu/OpenFPGA/blob/c393ee695975c98342b8708c5bee19b677f4a062/openfpga_flow/scripts/run_fpga_flow.py#L473

        lut_size = None
        for arch_file in chip.get('fpga', 'xml'):
            tree = ET.parse(schema_path(arch_file))
            root = tree.getroot()
            if root.tag == 'architecture':
                lut_size = max([int(pb_type.find("input").get("num_pins"))
                                for pb_type in root.iter("pb_type")
                                if pb_type.get("class") == "lut"])

        if lut_size == None:
            chip.logger.error('Could not infer FPGA LUT size from architecture \
                files')
            os.sys.exit()

        with open('fpga_lutsize.tcl', 'w') as f:
            f.write('set lutsize ' + str(lut_size))

def post_process(chip, step):
     ''' Tool specific function to run after step execution
     '''
     
     exe = chip.get('flow',step,'exe')[-1]
     with open(exe + ".log") as f:
          for line in f:
               area = re.search('Chip area for module.*\:\s+(.*)', line)
               cells = re.search('Number of cells\:\s+(.*)', line)
               warnings = re.search('Warnings.*\s(\d+)\s+total', line)
               
               if area:
                    chip.set('real', step, 'cell_area', str(round(float(area.group(1)),2)))
               elif cells:
                    chip.set('real', step, 'cells', cells.group(1))
               elif warnings:
                    chip.set('real', step, 'warnings', warnings.group(1))
