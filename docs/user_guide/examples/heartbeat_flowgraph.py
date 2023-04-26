###
# This is a docs example, referenced by its comments.
#
#   Runs to completion with SC v0.11.0
##

import siliconcompiler                         # import python package
chip = siliconcompiler.Chip('heartbeat')       # create chip object

# set up design
chip.set('input', 'rtl', 'verilog', 'heartbeat.v')           # define list of source files
chip.set('input', 'constraint', 'sdc', 'heartbeat.sdc')      # set constraints file

# set up pdk, libs and flow
chip.load_target('freepdk45_demo')             # load freepdk45

# modify flowgraph:
# start of flowgraph setup <docs reference>
flow = 'synflow'
chip.node(flow, 'import', 'surelog', 'import') # use surelog for import
chip.node(flow, 'syn', 'yosys', 'syn_asic')    # use yosys for synthesis
chip.edge(flow, 'import', 'syn')               # perform syn after import
chip.set('option', 'flow', flow)
# end of flowgraph setup <docs reference>

# compiles and sumarizes design info   
chip.run()                                     # run compilation
chip.summary()                                 # print results summary
