import siliconcompiler

chip = siliconcompiler.Chip()           # create chip object

# Technology setup
chip.target("freepdk45")                # set up pdk

# Flow creation
chip.node('import', 'surelog')          # define import task
chip.node('syn', 'yosys')               # define logical synthesis task
chip.edge('import', 'syn')              # define logical synthesis task

# Design
chip.add('source','add.v')              # load source files
chip.set('design','add')                # set top module
chip.set('clock','clk','pin','clk')     # bind pin 'clk' to clock name 'clk'
chip.set('clock','clk','period',1.0)    # define clock period of clock 'clk'

# Options
chip.set('quiet', True)                 # Redirect tool outputs to file

# Compile
chip.run()                              # run compilation

# Results
chip.summary()                          # print summary
