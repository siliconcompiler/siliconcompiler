import siliconcompiler               # import python package
chip = siliconcompiler.Chip()        # create chip object
chip.target("freepdk45")             # load predefined target pdk
chip.node('import', 'surelog')       # create import task
chip.node('syn', 'yosys')            # create synthesis task
chip.node('floorplan', 'openroad')   # create floorplan task
chip.edge('import', 'syn')           # connect import-->syn
chip.edge('syn', 'floorplan')        # connect syn-->floorplan
chip.add('source','add.v')           # define list of source files
chip.set('design','add')             # set top module
chip.set('clock','clk','pin','clk')  # bind pin 'clk' to clock named 'clk'
chip.set('clock','clk','period',1.0) # define period of clock named 'clk'
chip.set('quiet', True)              # redirect tool output to log file
chip.run()                           # run compilation
chip.summary()                       # print results summary
