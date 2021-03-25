import os

################################
# Tool Setup
################################

def setup_tool(chip, step, tool):

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
          
def setup_options(chip,step , tool):
     
     options = chip.get('flow', step, 'option')
     return options

################################
# Pre/Post Processing
################################
def pre_process(chip, step, tool):
    ''' Tool specific function to run before step execution
    '''
    sc_paths = os.getenv('SCPATH').split(' ')
    sc_path = ''
    for path in sc_paths:
      if chip.cfg['pdk_foundry']['value'][-1] in path:
        sc_path = path
    sc_root = sc_path[:sc_path.find('/foundry')]
    foundry_path = '%s/%s/pdk/%s'%(
        sc_path,
        chip.cfg['target']['value'][-1],
        chip.cfg['pdk_rev']['value'][-1])
    lefs_path = '%s/%s/libs/%s/%s/lef'%(
        sc_path,
        chip.cfg['target']['value'][-1],
        chip.cfg['target_lib']['value'][0],
        chip.cfg['pdk_rev']['value'][-1])
    tech_file = '%s/setup/klayout/%s.lyt'%(
        foundry_path,
        chip.cfg['target']['value'][-1])
    if step == 'export':
         chip.add('flow', step, 'option', '-nn')
         chip.add('flow', step, 'option', tech_file)
         chip.add('flow', step, 'option', '-rd')
         chip.add('flow', step, 'option', 'design_name=%s'%(
             chip.cfg['design']['value'][-1]))
         chip.add('flow', step, 'option', '-rd')
         chip.add('flow', step, 'option', 'in_def=inputs/%s.def'%(
             chip.cfg['design']['value'][-1]))
         chip.add('flow', step, 'option', '-rd')
         chip.add('flow', step, 'option', 'seal_gds=""')
         chip.add('flow', step, 'option', '-rd')
         chip.add('flow', step, 'option', 'in_gds=%s/%s'%(
             sc_root,
             chip.cfg['stdcell'][chip.cfg['target_lib']['value'][0]]['gds']['value'][-1]))
         chip.add('flow', step, 'option', '-rd')
         chip.add('flow', step, 'option', 'out_gds=outputs/%s.gds'%(
             chip.cfg['design']['value'][-1]))
         chip.add('flow', step, 'option', '-rd')
         chip.add('flow', step, 'option', 'tech_file=%s'%tech_file)
         chip.add('flow', step, 'option', '-rd')
         chip.add('flow', step, 'option', 'foundry_lefs=%s'%lefs_path)
         chip.add('flow', step, 'option', '-rm')
         chip.add('flow', step, 'option', 'def2gds.py')

def post_process(chip, step, tool):
    ''' Tool specific function to run after step execution
    '''
    pass
