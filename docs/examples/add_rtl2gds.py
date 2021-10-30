import siliconcompiler

chip = siliconcompiler.Chip()           # create chip object

# Technology
chip.target("freepdk45")                # set up pdk

# Design
chip.add('source','add.v')              # load source files
chip.add('design','add')                # set top module
chip.set('clock','clk','pin','clk')     # bind pin 'clk' to clock name 'clk'
chip.set('clock','clk','period',1.0)    # define clock period of clock 'clk'

# Compilation flow
chip.node('import', 'surelog')          # define import task
chip.node('syn', 'yosys')               # define logical synthesis task
chip.node('physyn', 'openroad')         # define physical synthesis task
chip.node('floorplan', 'openroad')      # define floorplan task task
chip.node('cts', 'openroad')            # define floorplan task task
chip.node('route', 'openroad')          # define floorplan task task
chip.node('export', 'klayout')          # define floorplan task task

chip.edge('import', 'syn')              # import --> syn
chip.edge('syn', 'physyn')              # import --> syn
chip.edge('physyn', 'floorplan')              # import --> syn
chip.edge('floorplan', 'syn')              # import --> syn
chip.edge('import', 'syn')              # import --> syn
chip.edge('import', 'syn')              # import --> syn


chip.run()                              # run compilation
chip.summary()                          # print summary
