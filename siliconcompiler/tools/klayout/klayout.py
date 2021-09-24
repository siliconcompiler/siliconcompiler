import os
import re
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

    Installation: https://github.com/KLayout/klayout

    '''

    chip = siliconcompiler.Chip()
    chip.target('freepdk45')
    chip.set('arg','step','export')
    chip.set('arg','index','<index>')
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

    if mode == 'show':
        clobber = True
        script = '/klayout_show.py'
        option = '-nn'
    else:
        clobber = False
        script = '/klayout_export.py'
        option = '-zz'

    chip.set('eda', tool, step, index, 'exe', 'klayout', clobber=clobber)
    chip.set('eda', tool, step, index, 'copy', 'true', clobber=clobber)
    chip.set('eda', tool, step, index, 'refdir', refdir, clobber=clobber)
    chip.set('eda', tool, step, index, 'script', refdir + script, clobber=clobber)
    chip.set('eda', tool, step, index, 'vswitch', '-zz -v', clobber=clobber)
    chip.set('eda', tool, step, index, 'version', '0.26.10', clobber=clobber)
    chip.set('eda', tool, step, index, 'option', 'cmdline', option, clobber=clobber)

################################
#  Custom runtime options
################################

def runtime_options(chip):

    ''' Custom runtime options, returnst list of command line options.
    '''

    step = chip.get('arg','step')
    index = chip.get('arg','index')
    libname = chip.get('asic', 'targetlib')[0]
    pdk_rev = chip.get('pdk', 'version')
    lib_rev = chip.get('library', libname, 'version')
    stackup = chip.get('pdk','stackup')[0]
    libtype = chip.get('library', libname, 'arch')
    techfile = chip.find(chip.get('pdk','layermap', stackup, 'def', 'gds')[0])
    techlef = chip.find(chip.get('pdk','aprtech', stackup, libtype, 'lef')[0])
    #TODO: fix this!, is foundry_lefs they only way??
    #needed?
    liblef = chip.find(chip.get('library',libname,'lef')[0])
    lefpath = os.path.dirname(liblef)
    #TODO: fix to add fill
    config_file = ""

    #TODO: Fix fill file (once this is a python)
    #config_file = '%s/setup/klayout/fill.json'%(foundry_path)

    #TODO: Fix, currenly only accepts one GDS file, need to loop
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
            for gds in chip.get('library', lib, 'gds'):
                gds_files.append(chip.find(gds))
        for lib in chip.get('asic', 'macrolib'):
            for gds in chip.get('library', lib, 'gds'):
                gds_files.append(chip.find(gds))
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
            for lef in chip.get('library', lib, 'lef'):
                lef_files.append(chip.find(lef))
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

################################
# Version Check
################################

def check_version(chip, version):
    ''' Tool specific version checking
    '''
    step = chip.get('arg','step')
    index = chip.get('arg','index')
    required = chip.get('eda', 'klayout', step, index, 'version')
    #insert code for parsing the funtion based on some tool specific
    #semantics.
    #syntax for version is string, >=string

    return 0

################################
# Post_process (post executable)
################################

def post_process(chip):
    ''' Tool specific function to run after step execution
    '''
    # Pass along files needed for future verification steps
    design = chip.get('design')

    #TODO: Fix fur multi (this will be moved to run step)
    shutil.copy(f'inputs/{design}.def', f'outputs/{design}.def')
    shutil.copy(f'inputs/{design}.sdc', f'outputs/{design}.sdc')
    shutil.copy(f'inputs/{design}.vg', f'outputs/{design}.vg')

    return 0

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
