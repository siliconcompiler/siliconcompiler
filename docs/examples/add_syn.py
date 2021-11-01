import siliconcompiler                   # import python package

pdkname = "freepdk45"                    # name of predefined pdk
sources = ['add.v']                      # list of source files
topmodule = 'add'                        # name of top module
clk = 'clk'                              # name of clock
clkperiod = 1.0                          # clock period in nanoseconds

chip = siliconcompiler.Chip()            # create chip object
chip.target(pdkname)                     # load predefined pdk settings
chip.node('import', 'surelog')           # create import task
chip.node('syn', 'yosys')                # create synthesis task
chip.node('floorplan', 'openroad')       # create floorplan task
chip.edge('import', 'syn')               # connect import-->syn
chip.edge('syn', 'floorplan')            # connect syn-->floorplan
chip.add('source',sources)               # define list of source files
chip.set('design',topmodule)             # set top module
chip.set('clock',clk,'pin',clk)          # bind pin 'clk' to clock named 'clk'
chip.set('clock',clk,'period',clkperiod) # define period of clock named 'clk'
chip.set('quiet', True)                  # redirect tool output to log file
chip.run()                               # run compilation
chip.summary()                           # print results summary
