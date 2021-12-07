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
        option = '-zz'

    chip.set('eda', tool, step, index, 'exe', klayout_exe, clobber=clobber)
    chip.set('eda', tool, step, index, 'copy', 'true', clobber=clobber)
    chip.set('eda', tool, step, index, 'refdir', refdir, clobber=clobber)
    chip.set('eda', tool, step, index, 'script', refdir + script, clobber=clobber)
    chip.set('eda', tool, step, index, 'vswitch', '-zz -v', clobber=clobber)
    chip.set('eda', tool, step, index, 'version', '0.26.11', clobber=clobber)

    chip.set('eda', tool, step, index, 'option', option, clobber=clobber)

    # Input/Output requirements
    chip.add('eda', tool, step, index, 'output', chip.get('design') + '.gds')

    # Adding requirements
    targetlibs = chip.get('asic', 'targetlib')
    stackup = chip.get('asic', 'stackup')
    if bool(stackup) & bool(targetlibs):
        mainlib = targetlibs[0]
        macrolibs = chip.get('asic', 'macrolib')

        chip.add('eda', tool, step, index, 'require', ",".join(['asic', 'targetlib']))
        chip.add('eda', tool, step, index, 'require', ",".join(['asic', 'stackup']))
        chip.add('eda', tool, step, index, 'require', ",".join(['pdk', 'layermap', stackup, 'def','gds']))

        for lib in (targetlibs + macrolibs):
            chip.add('eda', tool, step, index, 'require', ",".join(['library', lib, 'gds']))
            chip.add('eda', tool, step, index, 'require', ",".join(['library', lib, 'lef']))
    else:
        chip.error = 1
        chip.logger.error(f'Stackup and targetlib paremeters required for OpenROAD.')


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

    step = chip.get('arg','step')
    index = chip.get('arg','index')
    libname = chip.get('asic', 'targetlib')[0]
    pdk_rev = chip.get('pdk', 'version')
    lib_rev = chip.get('library', libname, 'package', 'version')
    stackup = chip.get('pdk','stackup')[0]
    libtype = chip.get('library', libname, 'arch')
    techfile = chip.find_files('pdk','layermap', stackup, 'def', 'gds')[0]
    #TODO: fix this!, is foundry_lefs they only way??
    #needed?
    liblef = chip.find_files('library',libname,'lef')[0]
    lefpath = os.path.dirname(liblef) if liblef else None
    #TODO: fix to add fill
    config_file = ""

    #TODO: Fix fill file (once this is a python)
    #config_file = '%s/setup/klayout/fill.json'%(foundry_path)

    if step == 'export':
        options = []
        options.append('-rd')
        options.append('design_name=%s'%(chip.get('design')))
        options.append('-rd')
        options.append('in_def=inputs/%s.def'%(chip.get('design')))
        options.append('-rd')
        options.append('seal_file=""')
        options.append('-rd')
        gds_files = []
        for lib in chip.get('asic', 'targetlib'):
            for gds in chip.find_files('library', lib, 'gds'):
                gds_files.append(gds)
        for lib in chip.get('asic', 'macrolib'):
            for gds in chip.find_files('library', lib, 'gds'):
                gds_files.append(gds)
        gds_list = ' '.join(gds_files)
        options.append(f'in_files="{gds_list}"')
        options.append('-rd')
        options.append('out_file=outputs/%s.gds'%(chip.get('design')))
        options.append('-rd')
        options.append('tech_file=%s'%techfile)
        options.append('-rd')
        options.append('foundry_lefs=%s'%lefpath)
        lef_files = []
        #for lib in chip.get('asic', 'targetlib'):
        #    for lef in chip.get('library', lib, 'lef'):
        #        lef_files.append(chip.find(lef))
        for lib in chip.get('asic', 'macrolib'):
            for lef in chip.find_files('library', lib, 'lef'):
                lef_files.append(lef)
        lef_list = ' '.join(lef_files)
        options.append('-rd')
        options.append(f'macro_lefs="{lef_list}"')
        options.append('-rd')
        if os.path.isfile(config_file):
            options.append('config_file=%s'%config_file)
        else:
            options.append('config_file=""')
        options.append('-r')
        options.append('klayout_export.py')

        return options
    elif step.startswith('show'):
        return []

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
