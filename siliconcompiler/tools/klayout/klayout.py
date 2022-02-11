import os
import platform
import re
import shutil
import siliconcompiler
from pathlib import Path

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

    chip = siliconcompiler.Chip()
    chip.load_target('freepdk45_demo')
    chip.set('arg','step','export')
    chip.set('arg','index','<index>')
    chip.set('design', '<design>')
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
                chip.set('eda', tool, 'path', loc_dir)
            elif os.path.isdir(global_dir):
                chip.set('eda', tool, 'path', global_dir)
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
                chip.set('eda', tool, 'path', klayout_dir)
            elif os.path.isdir(klayout_brew_dir):
                chip.set('eda', tool, 'path', klayout_brew_dir)
    else:
        klayout_exe = 'klayout'

    if mode == 'show':
        clobber = False
        script = '/klayout_show.py'
        option = ['-nc', '-rm']
    else:
        clobber = False
        script = '/klayout_export.py'
        option = ['-zz', '-r']

    chip.set('eda', tool, 'exe', klayout_exe, clobber=True)
    chip.set('eda', tool, 'vswitch', ['-zz', '-v'], clobber=clobber)
    chip.set('eda', tool, 'version', '0.26.11', clobber=clobber)
    chip.set('eda', tool, 'format', 'json', clobber=clobber)
    chip.set('eda', tool, 'copy', 'true', clobber=clobber)
    chip.set('eda', tool, 'refdir', step, index, refdir, clobber=clobber)
    chip.set('eda', tool, 'script', step, index, refdir + script, clobber=clobber)
    chip.set('eda', tool, 'option', step, index, option, clobber=clobber)

    # Export GDS with timestamps by default.
    chip.set('eda', tool, 'variable', step, index, 'timestamps', 'true', clobber=False)

    # Input/Output requirements
    if (not chip.valid('read', 'def', step, index) or
        not chip.get('read', 'def', step, index)):
        chip.add('eda', tool, 'input', step, index, chip.get('design') + '.def')
    chip.add('eda', tool, 'output', step, index, chip.get('design') + '.gds')

    # Adding requirements
    if mode != 'show':
        targetlibs = chip.get('asic', 'logiclib')
        stackup = chip.get('asic', 'stackup')
        if bool(stackup) & bool(targetlibs):
            macrolibs = chip.get('asic', 'macrolib')

            chip.add('eda', tool, 'require', step, index, ",".join(['asic', 'logiclib']))
            chip.add('eda', tool, 'require', step, index, ",".join(['asic', 'stackup']))
            chip.add('eda', tool, 'require', step, index,  ",".join(['pdk', 'layermap', 'klayout', stackup, 'def','gds']))

            for lib in (targetlibs + macrolibs):
                chip.add('eda', tool, 'require', step, index, ",".join(['library', lib, 'gds']))
                chip.add('eda', tool, 'require', step, index, ",".join(['library', lib, 'lef']))
        else:
            chip.error = 1
            chip.logger.error(f'Stackup and targetlib paremeters required for Klayout.')




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


################################
# Post_process (post executable)
################################

def post_process(chip):
    ''' Tool specific function to run after step execution
    '''

    tool = 'klayout'
    step = chip.get('arg', 'step')
    index = chip.get('arg','index')
    logfile = f"{step}.log"

    # Log file parsing
    chip.set('eda', tool, 'regex', step, index, 'warnings', "WARNING", clobber=False)
    chip.set('eda', tool, 'regex', step, index, 'errors', "ERROR", clobber=False)

    # Reports
    for metric in ('errors', 'warnings'):
        chip.set('eda', tool, 'report', step, index, metric, logfile)

    return 0

##################################################
if __name__ == "__main__":
    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'

    # create a chip instance
    chip = siliconcompiler.Chip()
    chip.load_target("freepdk45_demo")
    # load configuration
    setup(chip, step='export', index='0')
    # write out results
    chip.writecfg(output)
