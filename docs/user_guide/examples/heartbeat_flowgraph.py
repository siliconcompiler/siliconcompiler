import siliconcompiler                     # import python package
chip = siliconcompiler.Chip()              # create chip object
chip.set('source', 'heartbeat.v')          # define list of source files
chip.set('design', 'heartbeat')            # set top module
chip.set('constraint', 'heartbeat.sdc')    # set constraints file
chip.load_target('freepdk45_demo')         # load freepdk45
# start of flowgraph setup
flow = 'synflow'
chip.node(flow, 'import', 'surelog')       # use surelog for import
chip.node(flow, 'syn', 'yosys')            # use yosys for synthesis
chip.edge(flow, 'import', 'syn')           # perform syn after import
chip.set('flow', flow)
# end of flowgraph setup
chip.run()                                 # run compilation
chip.summary()                             # print results summary
