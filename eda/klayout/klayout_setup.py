import os
import re

################################
# Tool Setup
################################

def setup_tool(chip, step):

     refdir = 'eda/klayout'
     
     for step in (['export', 'gdsview']):
          chip.add('flow', step, 'threads', '4')
          chip.add('flow', step, 'format', 'json')
          chip.add('flow', step, 'copy', 'true')
          chip.add('flow', step, 'vendor', 'klayout')
          chip.add('flow', step, 'exe', 'klayout') 
          chip.add('flow', step, 'refdir', refdir)
          if step == 'gdsview':               
               chip.add('flow', step, 'option', '-nn')
          elif step == 'export':               
               chip.add('flow', step, 'option', '-zz')
          
def setup_options(chip,step):

     options = chip.get('flow', step, 'option')

     scriptdir = os.path.dirname(os.path.abspath(__file__))
     sc_root   =  re.sub('siliconcompiler/eda/klayout',
                         'siliconcompiler',
                         scriptdir)
     sc_path = sc_root + '/asic'

     # TODO: should support multiple target libs?
     libname = chip.get('asic', 'targetlib')[-1]
     pdk_rev = chip.get('pdk', 'rev')[-1]
     lib_rev = chip.get('stdcell', libname, 'rev')[-1]

     foundry_path = f'%s/%s/%s/pdk/{pdk_rev}'%(
          sc_path,
          chip.cfg['pdk']['foundry']['value'][-1],
          chip.cfg['target']['value'][-1])
     lefs_path = f'%s/%s/%s/libs/{libname}/{lib_rev}/lef'%(
          sc_path,
          chip.cfg['pdk']['foundry']['value'][-1],
          chip.cfg['target']['value'][-1])
     tech_file = '%s/setup/klayout/%s.lyt'%(
          foundry_path,
          chip.cfg['target']['value'][-1])

     if step == 'export':
          options.append('-rd')
          options.append('design_name=%s'%(
               chip.cfg['design']['value'][-1]))
          options.append('-rd')
          options.append('in_def=inputs/%s.def'%(
               chip.cfg['design']['value'][-1]))
          options.append('-rd')
          options.append('seal_file=""')
          options.append('-rd')
          options.append('in_files=%s/%s'%(
               sc_root,
               chip.cfg['stdcell'][libname]['gds']['value'][-1]))
          options.append('-rd')
          options.append('out_file=outputs/%s.gds'%(
               chip.cfg['design']['value'][-1]))
          options.append('-rd')
          options.append('tech_file=%s'%tech_file)
          options.append('-rd')
          options.append('config_file=""')
          options.append('-rd')
          options.append('foundry_lefs=%s'%lefs_path)
          options.append('-rm')
          options.append('def2stream.py')

     return options

################################
# Pre/Post Processing
################################
def pre_process(chip, step):
    ''' Tool specific function to run before step execution
    '''
    pass

def post_process(chip, step):
    ''' Tool specific function to run after step execution
    '''
    pass
