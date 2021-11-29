import siliconcompiler                     # import python package
chip = siliconcompiler.Chip()              # create chip object
chip.set('source', 'heartbeat.v')          # define list of source files
chip.set('design', 'heartbeat')            # set top module
chip.set('constraint', 'heartbeat.sdc')    # set constraints file
chip.target('freepdk45')                   # load freepdk45
# start of flowgraph setup
chip.node('import', 'surelog')             # use surelog for import
chip.node('syn', 'yosys')                  # use yosys for synthesis
chip.edge('import', 'syn')                 # perform syn after import
# end of flowgraph setup
chip.run()                                 # run compilation
chip.summary()                             # print results summary
