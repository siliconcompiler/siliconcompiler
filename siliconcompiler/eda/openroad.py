
import os
import siliconcompiler as sc

####################################################
# Setup
####################################################

def setup_openroad(chip):

     #local variables
     edadir = ""
     threads = 4

     # common defaults
     for stage in chip.get('sc_stages'):
          chip.add('sc_tool', stage, 'np', threads)
          chip.add('sc_tool', stage, 'refdir', edadir)
          chip.add('sc_tool', stage, 'format', 'tcl')
          chip.add('sc_tool', stage, 'copy', 'no')
          
     # import
     chip.add('sc_tool', 'import', 'exe', 'verilator')
     chip.add('sc_tool', 'import', 'opt', '--lint-only --debug')
          
     # syn
     chip.add('sc_tool', 'syn', 'exe', 'yosys')
     chip.add('sc_tool', 'syn', 'opt', '-c')
     chip.add('sc_tool', 'syn', 'vendor', 'yosys')
     chip.add('sc_tool', 'syn', 'script', 'sc_syn.tcl')
     
     # pnr
     for stage in ('floorplan', 'place', 'cts', 'route', 'signoff'):
          chip.add('sc_tool', stage, 'script', 'sc_'+stage+'.tcl')
          chip.add('sc_tool', stage, 'exe', 'openroad')
          chip.add('sc_tool', stage, 'vendor', 'openroad')
          chip.add('sc_tool', stage, 'opt', '-no_init -exit')
               
     # export
     chip.add('sc_tool', 'export', 'exe', 'klayout')

#########################
if __name__ == "__main__":    

    # files
    fileroot = os.path.splitext(os.path.abspath(__file__))[0]
    jsonfile = fileroot + '.json'
    # create a chip instance
    chip = sc.Chip()
    # load configuration
    setup_openroad(chip)
    # write out storage file
    chip.writecfg(jsonfile)



           
