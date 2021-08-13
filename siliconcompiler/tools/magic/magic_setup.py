import os
import re
import shutil

from siliconcompiler.tools.magic import count_lvs

import siliconcompiler
from siliconcompiler.floorplan import *
from siliconcompiler.schema import schema_path

################################
# Setup Tool (pre executable)
################################

def setup_tool(chip, step):
    ''' Tool specific function to run before step execution
    '''

    tool = 'magic'
    refdir = 'siliconcompiler/tools/magic'

    target_tech = chip.get('target').split('_')[0]
    magicrc = '%s/magic/%s.magicrc'%(
        pdk_path(chip),
        target_tech)

    # magic used for drc and lvs
    if step == 'drc':
        script = 'gds_drc.tcl'
    elif step == 'lvs':
        script = 'lvs.tcl'

    chip.set('eda', tool, step, 'vendor', tool)
    chip.set('eda', tool, step, 'exe', tool)
    chip.set('eda', tool, step, 'format', 'tcl')
    chip.set('eda', tool, step, 'threads', '4')
    chip.set('eda', tool, step, 'copy', 'false')
    chip.set('eda', tool, step, 'refdir', refdir)
    chip.set('eda', tool, step, 'script', refdir + '/' + script)

    # set options
    options = []
    options.append('-rcfile')
    options.append(magicrc)
    options.append('-noc')
    options.append('-dnull')

    chip.set('eda', tool, step, 'option', 'cmdline', options)

    # Dumps path to PDK to tcl file so that .magicrc can find tech file
    with open('pdkpath.tcl', 'w') as f:
        f.write(f'set PDKPATH {pdk_path(chip)}')

################################
# Post_process (post executable)
################################

def post_process(chip, step):
    ''' Tool specific function to run after step execution

    Reads error count from output and fills in appropriate entry in metrics
    '''
    design = chip.get('design')

    if step == 'drc':
        with open(f'outputs/{design}.drc', 'r') as f:
            for line in f:
                errors = re.search(r'^\[INFO\]: COUNT: (\d+)', line)

                if errors:
                    chip.set('metric', step, 'real', 'errors', errors.group(1))
    elif step == 'lvs':
        # Export metrics
        lvs_failures = count_lvs.count_LVS_failures(f'outputs/{design}.lvs.json')
        chip.set('metric', step, 'real', 'errors', lvs_failures[0])

    # Need to pass along DEF and GDS to future verification stages
    shutil.copy(f'inputs/{design}.def', f'outputs/{design}.def')
    shutil.copy(f'inputs/{design}.gds', f'outputs/{design}.gds')

    #TODO: return error code
    return 0

################################
# Utilities
################################

def pdk_path(chip):
    scriptdir = os.path.dirname(os.path.abspath(__file__))
    sc_root   =  re.sub('siliconcompiler/siliconcompiler/tools/magic',
                        'siliconcompiler',
                        scriptdir)
    sc_path = sc_root + '/third_party/foundry'

    libname = chip.get('asic', 'targetlib')[0]
    pdk_rev = chip.get('pdk', 'rev')
    lib_rev = chip.get('stdcell', libname, 'rev')

    target_tech = chip.get('target').split('_')[0]

    return f'%s/%s/%s/pdk/{pdk_rev}/setup/'%(
        sc_path,
        chip.get('pdk', 'foundry'),
        target_tech)
