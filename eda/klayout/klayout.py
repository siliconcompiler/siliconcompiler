import os

def setup_tool(chip, step):

     refdir = 'eda/klayout'
     
     for stage in (['export', 'gdsview']):
          chip.add('flow', stage, 'threads', '4')
          chip.add('flow', stage, 'format', 'json')
          chip.add('flow', stage, 'copy', 'true')
          chip.add('flow', stage, 'vendor', 'klayout')
          chip.add('flow', stage, 'exe', 'klayout') 
          chip.add('flow', stage, 'refdir', refdir)
          if stage == 'gdsview':               
               chip.add('flow', stage, 'opt', '-nn')
          elif stage == 'export':               
               chip.add('flow', stage, 'opt', '-zz')

def setup_options(chip,stage):
     
     options = chip.get('flow', stage, 'opt')
     return options

################################
# Pre and Post Run Commands
################################
# TODO: Adapt to other PDKs besides freepdk45.
def pre_process(chip,step):
    ''' Tool specific function to run before step execution
    '''
    foundry_path = '%s/foundry/%s/%s/pdk/%s'%(os.getenv('SCPATH'), chip.cfg['pdk_foundry']['value'][-1], chip.cfg['target']['value'][-1], chip.cfg['pdk_rev']['value'][-1])
    lefs_path = '%s/foundry/%s/%s/libs/%s/%s/lef'%(os.getenv('SCPATH'), chip.cfg['pdk_foundry']['value'][-1], chip.cfg['target']['value'][-1], chip.cfg['target_lib']['value'][0], chip.cfg['pdk_rev']['value'][-1])
    tech_file = '%s/setup/klayout/%s.lyt'%(foundry_path, chip.cfg['target']['value'][-1])
    if step == 'export':
         chip.add('flow', step, 'opt', '-nn')
         chip.add('flow', step, 'opt', tech_file)
         chip.add('flow', step, 'opt', '-rd')
         chip.add('flow', step, 'opt', 'design_name=%s'%chip.cfg['design']['value'][-1])
         chip.add('flow', step, 'opt', '-rd')
         chip.add('flow', step, 'opt', 'in_def=inputs/%s.def'%chip.cfg['design']['value'][-1])
         chip.add('flow', step, 'opt', '-rd')
         chip.add('flow', step, 'opt', 'seal_gds=""')
         chip.add('flow', step, 'opt', '-rd')
         chip.add('flow', step, 'opt', 'in_gds=%s/%s'%(os.getenv('SCPATH'), chip.cfg['stdcell'][chip.cfg['target_lib']['value'][0]]['gds']['value'][-1]))
         chip.add('flow', step, 'opt', '-rd')
         chip.add('flow', step, 'opt', 'out_gds=outputs/%s.gds'%chip.cfg['design']['value'][-1])
         chip.add('flow', step, 'opt', '-rd')
         chip.add('flow', step, 'opt', 'tech_file=%s'%tech_file)
         chip.add('flow', step, 'opt', '-rd')
         chip.add('flow', step, 'opt', 'foundry_lefs=%s'%lefs_path)
         chip.add('flow', step, 'opt', '-rm')
         chip.add('flow', step, 'opt', 'def2gds.py')

def post_process(chip,step):
    ''' Tool specific function to run after step execution
    '''
    pass
