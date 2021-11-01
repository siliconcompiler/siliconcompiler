import siliconcompiler

chip = siliconcompiler.Chip()           # create chip object

# Technology setup
chip.target("freepdk45")                # set up pdk

# Create tasks flow graph
chip.node('import', 'surelog')          # import task
chip.node('syn', 'yosys')               # synthesis task
chip.node('floorplan', 'openroad')      # floorplan task
chip.edge('import', 'syn')              # connect import-->syn
chip.edge('syn', 'floorplan')           # connect syn-->floorplan
chip.write_flowgraph("add_syn.png")

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
