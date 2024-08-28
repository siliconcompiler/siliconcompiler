
'''
Klayout is a production grade viewer and editor of GDSII and
Oasis data with customizable Python and Ruby interfaces.

Documentation: https://www.klayout.de

Sources: https://github.com/KLayout/klayout

Installation: https://www.klayout.de/build.html
'''

import os
from pathlib import Path
import platform
import shutil
from siliconcompiler.tools._common import get_tool_task
from siliconcompiler.targets import freepdk45_demo


####################################################################
# Make Docs
####################################################################
def make_docs(chip):
    chip.use(freepdk45_demo)


####################################################################
# Setup tool
####################################################################
def setup(chip, mode="batch"):
    '''
    Setup function for Klayout
    '''

    tool = 'klayout'
    refdir = 'tools/' + tool
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)
    clobber = False

    klayout_exe = 'klayout'
    if chip.get('option', 'scheduler', 'name', step=step, index=index) != 'docker':
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

    # common to all
    chip.set('tool', tool, 'exe', klayout_exe)
    chip.set('tool', tool, 'vswitch', ['-zz', '-v'])
    chip.set('tool', tool, 'version', '>=0.28.0', clobber=clobber)
    chip.set('tool', tool, 'format', 'json', clobber=clobber)

    chip.set('tool', tool, 'task', task, 'refdir', refdir, step=step, index=index,
             package='siliconcompiler', clobber=clobber)

    if chip.get('option', 'nodisplay'):
        # Tells QT to use the offscreen platform if nodisplay is used
        chip.set('tool', tool, 'task', task, 'env', 'QT_QPA_PLATFORM', 'offscreen',
                 step=step, index=index)

    # Log file parsing
    chip.set('tool', tool, 'task', task, 'regex', 'warnings', r'(WARNING|warning)',
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'regex', 'errors', r'ERROR',
             step=step, index=index, clobber=False)


def runtime_options(chip):
    # Provide KLayout with path to SC package so the driver can import the
    # schema package directly. Since KL may be using a different Python
    # environment than the user, it needs to import the limited Schema class
    # that has no 3rd-party dependencies.
    # This must be done at runtime to work in a remote context.

    return ['-rd', f'SC_ROOT={chip.scroot}']


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
