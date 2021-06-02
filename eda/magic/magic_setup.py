import os
import re

################################
# Tool Setup
################################

def setup_tool(chip, step):

    refdir = 'eda/magic'

    chip.add('flow', step, 'threads', '4')
    chip.add('flow', step, 'format', 'tcl')
    chip.add('flow', step, 'copy', 'true')
    chip.add('flow', step, 'vendor', 'magic')
    chip.add('flow', step, 'exe', 'magic')
    chip.add('flow', step, 'refdir', refdir)
    chip.add('flow', step, 'script', refdir + '/gds_drc.tcl')

def setup_options(chip,step):
    options = chip.get('flow', step, 'option')

    target_tech = chip.cfg['target']['value'][-1].split('_')[0]

    magicrc = '%s/%s.magicrc'%(
        pdk_path(chip),
        target_tech)

    options.append('-rcfile')
    options.append(magicrc)
    options.append('-noc')
    options.append('-dnull')

    return options

################################
# Pre/Post Processing
################################

def pre_process(chip, step):
    ''' Tool specific function to run before step execution

    Dumps path to PDK to tcl file so that .magicrc can find tech file
    '''
    with open('pdkpath.tcl', 'w') as f:
        f.write(f'set PDKPATH {pdk_path(chip)}')

def post_process(chip, step):
    ''' Tool specific function to run after step execution
    '''
    pass

################################
# Utilities
################################

def pdk_path(chip):
    scriptdir = os.path.dirname(os.path.abspath(__file__))
    sc_root   =  re.sub('siliconcompiler/eda/magic',
                        'siliconcompiler',
                        scriptdir)
    sc_path = sc_root + '/asic'

    libname = chip.get('asic', 'targetlib')[-1]
    pdk_rev = chip.get('pdk', 'rev')[-1]
    lib_rev = chip.get('stdcell', libname, 'rev')[-1]

    target_tech = chip.cfg['target']['value'][-1].split('_')[0]

    return f'%s/%s/%s/pdk/{pdk_rev}/setup/magic'%(
        sc_path,
        chip.cfg['pdk']['foundry']['value'][-1],
        target_tech)
