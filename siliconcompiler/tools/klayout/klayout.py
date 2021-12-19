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
    chip.target('freepdk45')
    chip.set('arg','step','export')
    chip.set('arg','index','<index>')
    chip.set('design', '<design>')
    setup_tool(chip)

    return chip

####################################################################
# Setup tool
####################################################################

def setup_tool(chip, mode="batch"):
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
                                      'Program Files (x86)',
                                      'KLayout')
            if os.path.isdir(loc_dir):
                os.environ['PATH'] = os.environ['PATH'] + ';' + loc_dir
            elif os.path.isdir(global_dir):
                os.environ['PATH'] = os.environ['PATH'] + ';' + global_dir
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

    chip.set('eda', tool, 'exe', klayout_exe, clobber=clobber)
    chip.set('eda', tool, 'vswitch', '-zz -v', clobber=clobber)
    chip.set('eda', tool, 'version', '0.26.11', clobber=clobber)
    chip.set('eda', tool, 'format', 'json', clobber=clobber)
    chip.set('eda', tool, 'copy', 'true', clobber=clobber)
    chip.set('eda', tool, 'refdir', step, index, refdir, clobber=clobber)
    chip.set('eda', tool, 'script', step, index, refdir + script, clobber=clobber)
    chip.set('eda', tool, 'option', step, index, option, clobber=clobber)

    # Export GDS with timestamps by default.
    chip.set('eda', tool, 'variable', step, index, 'timestamps', 'true', clobber=False)

    # Input/Output requirements
    chip.add('eda', tool, 'output', step, index, chip.get('design') + '.gds')

    # Adding requirements
    if mode != 'show':
        targetlibs = chip.get('asic', 'targetlib')
        stackup = chip.get('asic', 'stackup')
        if bool(stackup) & bool(targetlibs):
            macrolibs = chip.get('asic', 'macrolib')

            chip.add('eda', tool, 'require', step, index, ",".join(['asic', 'targetlib']))
            chip.add('eda', tool, 'require', step, index, ",".join(['asic', 'stackup']))
            chip.add('eda', tool, 'require', step, index,  ",".join(['pdk', 'layermap', stackup, 'def','gds']))

            for lib in (targetlibs + macrolibs):
                chip.add('eda', tool, 'require', step, index, ",".join(['library', lib, 'gds']))
                chip.add('eda', tool, 'require', step, index, ",".join(['library', lib, 'lef']))
        else:
            chip.error = 1
            chip.logger.error(f'Stackup and targetlib paremeters required for KLayout.')


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
    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'

    # create a chip instance
    chip = siliconcompiler.Chip()
    chip.target("freepdk45")
    # load configuration
    setup_tool(chip, step='export', index='0')
    # write out results
    chip.writecfg(output)
