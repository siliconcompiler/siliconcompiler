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
    refdir = 'tools/'+tool
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    if platform.system() == 'Windows':
        klayout_exe = 'klayout_app.exe'
        if not shutil.which(klayout_exe):
            loc_dir = os.path.join(Path.home(), 'AppData', 'Roaming', 'KLayout')
            global_dir = os.path.join(os.path.splitdrive(Path.home())[0],
                                      os.path.sep,
                                      'Program Files (x86)',
                                      'KLayout')
            if os.path.isdir(loc_dir):
                chip.set('tool', tool, 'path', loc_dir)
            elif os.path.isdir(global_dir):
                chip.set('tool', tool, 'path', global_dir)
    elif platform.system() == 'Darwin':
        klayout_exe = 'klayout'
        if not shutil.which(klayout_exe):
            klayout_dir = os.path.join(os.path.sep,
                                       'Applications',
                                       'klayout.app',
                                       'Contents',
                                       'MacOS')
            # different install directory when installed using Homebrew
            klayout_brew_dir = os.path.join(os.path.sep,
                                            'Applications',
                                            'KLayout',
                                            'klayout.app',
                                            'Contents',
                                            'MacOS')
            if os.path.isdir(klayout_dir):
                chip.set('tool', tool, 'path', klayout_dir)
            elif os.path.isdir(klayout_brew_dir):
                chip.set('tool', tool, 'path', klayout_brew_dir)
    else:
        klayout_exe = 'klayout'

    if mode == 'show':
        clobber = False
        script = 'klayout_show.py'
        option = ['-nc', '-rm']
    else:
        clobber = False
        script = 'klayout_export.py'
        option = ['-zz', '-r']

    chip.set('tool', tool, 'exe', klayout_exe)
    chip.set('tool', tool, 'vswitch', ['-zz', '-v'])
    # Versions < 0.27.6 may be bundled with an incompatible version of Python.
    chip.set('tool', tool, 'version', '>=0.27.6', clobber=clobber)
    chip.set('tool', tool, 'format', 'json', clobber=clobber)
    chip.set('tool', tool, 'refdir', step, index, refdir, clobber=clobber)
    chip.set('tool', tool, 'script', step, index, script, clobber=clobber)
    chip.set('tool', tool, 'option', step, index, option, clobber=clobber)

    # Export GDS with timestamps by default.
    chip.set('tool', tool, 'var', step, index, 'timestamps', 'true', clobber=False)

    design = chip.top()

    # Input/Output requirements for default flow
    if step in ['export']:
        if (not chip.valid('input', 'def') or
            not chip.get('input', 'def')):
            chip.add('tool', tool, 'input', step, index, design + '.def')
        chip.add('tool', tool, 'output', step, index, design + '.gds')

    # Adding requirements
    if mode != 'show':
        targetlibs = chip.get('asic', 'logiclib')
        stackup = chip.get('asic', 'stackup')
        pdk = chip.get('option', 'pdk')
        if bool(stackup) & bool(targetlibs):
            macrolibs = chip.get('asic', 'macrolib')

            chip.add('tool', tool, 'require', step, index, ",".join(['asic', 'logiclib']))
            chip.add('tool', tool, 'require', step, index, ",".join(['asic', 'stackup']))
            chip.add('tool', tool, 'require', step, index,  ",".join(['pdk', pdk, 'layermap', 'klayout', 'def','gds', stackup]))

            for lib in (targetlibs + macrolibs):
                chip.add('tool', tool, 'require', step, index, ",".join(['library', lib, 'model', 'layout', 'gds', stackup]))
                chip.add('tool', tool, 'require', step, index, ",".join(['library', lib, 'model', 'layout', 'lef', stackup]))
        else:
            chip.error(f'Stackup and targetlib paremeters required for Klayout.')

    logfile = f"{step}.log"

    # Log file parsing
    chip.set('tool', tool, 'regex', step, index, 'warnings', "WARNING", clobber=False)
    chip.set('tool', tool, 'regex', step, index, 'errors', "ERROR", clobber=False)

################################
#  Environment setup
################################

def setup_env(chip):
    '''
    Creates environment setup files in the current directory.

    Setup is based on the parameters passed in through the chip object.

    '''

    return 0

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
