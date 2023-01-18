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
    tasks = ('export', 'show', 'screenshot')
    clobber = False

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

    for task in tasks:
        # common to all
        chip.set('tool', tool, 'exe', klayout_exe)
        chip.set('tool', tool, 'vswitch', ['-zz', '-v'])
        # Versions < 0.27.6 may be bundled with an incompatible version of Python.
        chip.set('tool', tool, 'version', '>=0.27.6', clobber=clobber)
        chip.set('tool', tool, 'format', 'json', clobber=clobber)

        chip.set('tool', tool, 'task', task, 'refdir', step, index, refdir, clobber=clobber)

        # Export GDS with timestamps by default.
        chip.set('tool', tool, 'task', task, 'var', step, index, 'timestamps', 'true', clobber=False)

        # Log file parsing
        chip.set('tool', tool, 'task', task, 'regex', step, index, 'warnings', r'(WARNING|warning)', clobber=False)
        chip.set('tool', tool, 'task', task, 'regex', step, index, 'errors', r'ERROR', clobber=False)

################################
# Version Check
################################

def parse_version(stdout):
    # KLayout 0.26.11
    return stdout.split()[1]

def find_incoming_ext(chip):

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    flow = chip.get('option', 'flow')

    supported_ext = ('gds', 'oas', 'def')

    for input_step, input_index in chip.get('flowgraph', flow, step, index, 'input'):
        for ext in supported_ext:
            show_file = chip.find_result(ext, step=input_step, index=input_index)
            if show_file:
                return ext

    # Nothing found, just add last one
    return supported_ext[-1]

##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("klayout.json")
