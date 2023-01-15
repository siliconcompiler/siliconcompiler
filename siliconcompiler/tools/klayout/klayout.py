import os
from pathlib import Path
import platform
import shutil

import siliconcompiler

####################################################################
# Make Docs
####################################################################

def make_docs():
    '''
    Klayout is a production grade viewer and editor of GDSII and
    Oasis data with customizable Python and Ruby interfaces.

    Documentation: https://www.klayout.de

    Sources: https://github.com/KLayout/klayout

    Installation: https://www.klayout.de/build.html

    '''

    chip = siliconcompiler.Chip('<design>')
    chip.load_target('freepdk45_demo')
    chip.set('arg','step','export')
    chip.set('arg','index','<index>')
    setup(chip)

    return chip

####################################################################
# Setup tool
####################################################################

def setup(chip, mode="batch"):
    '''
    Setup function for Klayout
    '''

    tool = 'klayout'
    tasks = ['export', 'view']
    refdir = 'tools/'+tool
    step = chip.get('arg','step')
    index = chip.get('arg','index')
    design = chip.top()
    targetlibs = chip.get('asic', 'logiclib')
    stackup = chip.get('asic', 'stackup')
    pdk = chip.get('option', 'pdk')
    macrolibs = chip.get('asic', 'macrolib')

    if platform.system() == 'Windows':
        klayout_exe = 'klayout_app.exe'
        if not shutil.which(klayout_exe):
            loc_dir = os.path.join(Path.home(), 'AppData', 'Roaming', 'KLayout')
            if os.path.isdir(loc_dir):
                path = loc_dir
            else:
                path = os.path.join(os.path.splitdrive(Path.home())[0],
                                    os.path.sep,
                                    'Program Files (x86)',
                                    'KLayout')
    elif platform.system() == 'Darwin':
        klayout_exe = 'klayout'
        if not shutil.which(klayout_exe):
            klayout_dir = os.path.join(os.path.sep,
                                       'Applications',
                                       'klayout.app',
                                       'Contents',
                                       'MacOS')
            if os.path.isdir(klayout_dir):
                path = klayout_dir
            else:
                path = os.path.join(os.path.sep,
                                            'Applications',
                                            'KLayout',
                                            'klayout.app',
                                            'Contents',
                                            'MacOS')
    else:
        klayout_exe = 'klayout'
        path = ''

    if mode == 'show':
        clobber = False
        script = 'klayout_show.py'
        option = ['-nc', '-rm']
    else:
        clobber = False
        script = 'klayout_export.py'
        option = ['-b', '-r']

    # Tool options
    chip.set('tool', tool, 'exe', klayout_exe)
    chip.set('tool', tool, 'path', path)
    chip.set('tool', tool, 'vswitch', ['-zz', '-v'])
    # Versions < 0.27.6 may be bundled with an incompatible version of Python.
    chip.set('tool', tool, 'version', '>=0.27.6', clobber=clobber)
    chip.set('tool', tool, 'format', 'json', clobber=clobber)

    for task in tasks:

        chip.set('tool', tool, 'task', task, 'refdir', step, index, refdir, clobber=clobber)
        chip.set('tool', tool, 'task', task, 'script', step, index, script, clobber=clobber)
        chip.set('tool', tool, 'task', task, 'option', step, index, option, clobber=clobber)

        # Export GDS with timestamps by default.
        chip.set('tool', tool, 'task', task, 'var', step, index, 'timestamps', 'true', clobber=False)

        # Input/Output requirements for default flow
        if task in ['export']:

            if (not chip.valid('input', 'layout', 'def') or
                not chip.get('input', 'layout', 'def')):
                chip.add('tool', tool, 'task', task, 'input', step, index, design + '.def')
            chip.add('tool', tool, 'task', task, 'output', step, index, design + '.gds')

        # Adding requirements
        if mode != 'show':
            if bool(stackup) & bool(targetlibs):
                chip.add('tool', tool, 'task', task, 'require', step, index, ",".join(['asic', 'logiclib']))
                chip.add('tool', tool, 'task', task, 'require', step, index, ",".join(['asic', 'stackup']))
                chip.add('tool', tool, 'task', task, 'require', step, index,  ",".join(['pdk', pdk, 'layermap', 'klayout', 'def','gds', stackup]))

                for lib in (targetlibs + macrolibs):
                    chip.add('tool', tool, 'task', task, 'require', step, index, ",".join(['library', lib, 'output', stackup, 'gds']))
                    chip.add('tool', tool, 'task', task, 'require', step, index, ",".join(['library', lib, 'output', stackup, 'lef']))
            else:
                chip.error(f'Stackup and targetlib paremeters required for Klayout.')

        # Log file parsing
        chip.set('tool', tool, 'task', task, 'regex', step, index, 'warnings', r'(WARNING|warning)', clobber=False)
        chip.set('tool', tool, 'task', task, 'regex', step, index, 'errors', r'ERROR', clobber=False)

################################
#  Custom runtime options
################################

def runtime_options(chip):
    '''
    Custom runtime options, returns list of command line options.
    '''
    return []

################################
# Version Check
################################

def parse_version(stdout):
    # KLayout 0.26.11
    return stdout.split()[1]


##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("klayout.json")
