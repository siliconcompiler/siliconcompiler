import os
import re
import shutil
import siliconcompiler
from siliconcompiler.schema_utils import schema_path

def setup_tool(chip, step, index, mode="batch"):
    '''
    Setup function for Klayout
    '''

    tool = 'klayout'
    refdir = 'siliconcompiler/tools/klayout'
    if mode == 'show':
        clobber = True
        script = '/klayout_show.py'
        option = '-nn'
    else:
        clobber = False
        script = '/klayout_export.py'
        option = '-zz'

    chip.set('eda', tool, step, index, 'exe', 'klayout', clobber=clobber)
    chip.set('eda', tool, step, index, 'vendor', 'klayout', clobber=clobber)
    chip.set('eda', tool, step, index, 'copy', 'true', clobber=clobber)
    chip.set('eda', tool, step, index, 'refdir', refdir, clobber=clobber)
    chip.set('eda', tool, step, index, 'script', refdir + script, clobber=clobber)
    chip.set('eda', tool, step, index, 'vswitch', '-zz -v', clobber=clobber)
    chip.set('eda', tool, step, index, 'version', '0.26.10', clobber=clobber)
    chip.set('eda', tool, step, index, 'option', 'cmdline', option, clobber=clobber)

    scriptdir = os.path.dirname(os.path.abspath(__file__))
    sc_root =  re.sub('siliconcompiler/siliconcompiler/tools/klayout',
                      'siliconcompiler',
                      scriptdir)
    sc_path = sc_root + '/third_party/foundry'

    # TODO: should support multiple target libs?
    libname = chip.get('asic', 'targetlib')[0]
    pdk_rev = chip.get('pdk', 'version')
    lib_rev = chip.get('library', libname, 'version')
    targetlist = chip.get('target').split('_')
    platform =  targetlist[0]

    #TODO: pass in SC cfg file klayout python script?
    foundry_path = f'%s/%s/%s/pdk/{pdk_rev}'%(sc_path, chip.get('pdk','foundry'), platform)
    lefs_path = f'%s/%s/%s/libs/{libname}/{lib_rev}/lef'%(sc_path,chip.get('pdk','foundry'),platform)
    tech_file = '%s/setup/klayout/%s.lyt'%(foundry_path,platform)
    config_file = '%s/setup/klayout/fill.json'%(foundry_path)

    #TODO: Fix, currenly only accepts one GDS file, need to loop
    if step == 'export':
        options = []
        options.append('-rd')
        options.append('design_name=%s'%(chip.get('design')))
        options.append('-rd')
        options.append(f'in_def=inputs/%s.def'%(chip.get('design')))
        options.append('-rd')
        options.append('seal_file=""')
        options.append('-rd')
        stdcell_gds = chip.get('library', libname, 'gds')[0]
        gds_files = [f'{sc_root}/{stdcell_gds}']
        for macrolib in chip.get('asic', 'macrolib'):
            for gds in chip.get('library', macrolib, 'gds'):
                gds_files.append(schema_path(gds))
        gds_list = ' '.join(gds_files)
        options.append(f'in_files="{gds_list}"')
        options.append('-rd')
        options.append('out_file=outputs/%s.gds'%(chip.get('design')))
        options.append('-rd')
        options.append('tech_file=%s'%tech_file)
        options.append('-rd')
        if os.path.isfile(config_file):
            options.append('config_file=%s'%config_file)
        else:
            options.append('config_file=""')
        options.append('-rd')
        options.append('foundry_lefs=%s'%lefs_path)

        options.append('-rd')
        lef_files = []
        for macrolib in chip.get('asic', 'macrolib'):
            for lef in chip.get('library', macrolib, 'lef'):
                lef_files.append(schema_path(lef))
        lef_list = ' '.join(lef_files)
        options.append(f'macro_lefs="{lef_list}"')
        options.append('-r')
        options.append('klayout_export.py')

        #add all options to dictionary
        chip.add('eda', tool, step, index, 'option', 'cmdline', options)

################################
# Version Check
################################

def check_version(chip, step, index, version):
    ''' Tool specific version checking
    '''
    required = chip.get('eda', 'klayout', step, index, 'version')
    #insert code for parsing the funtion based on some tool specific
    #semantics.
    #syntax for version is string, >=string
    
    return 0

################################
# Post_process (post executable)
################################
        
def post_process(chip, step, index):
    ''' Tool specific function to run after step execution
    '''
    # Pass along files needed for future verification steps
    design = chip.get('design')

    #TODO: Fix fur multi (this will be moved to run step)
    shutil.copy(f'inputs/{design}.def', f'outputs/{design}.def')
    shutil.copy(f'inputs/{design}.sdc', f'outputs/{design}.sdc')
    shutil.copy(f'inputs/{design}.v', f'outputs/{design}.v')

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
