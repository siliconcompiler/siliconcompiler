###
# This is a docs example, referenced by its comments.
#
##

import os
import siliconcompiler                         # import python package
from siliconcompiler.targets import freepdk45_demo  # import target

# import pre-defined python packages for setting up tools used in flowgraph
from siliconcompiler.tools.surelog import parse
from siliconcompiler.tools.yosys import syn_asic

chip = siliconcompiler.Chip('heartbeat')       # create chip object

# set up design
root = os.path.dirname(__file__)
chip.set('input', 'rtl', 'verilog', f'{root}/heartbeat.v')           # define list of source files
chip.set('input', 'constraint', 'sdc', f'{root}/heartbeat.sdc')      # set constraints file

# set up pdk, libs and flow
chip.load_target(freepdk45_demo)             # load freepdk45

# modify flowgraph:
# start of flowgraph setup <docs reference>
flow = 'synonlyflow'
chip.node(flow, 'import', parse)               # use surelog for import
chip.node(flow, 'syn', syn_asic)               # use yosys for synthesis
chip.edge(flow, 'import', 'syn')               # perform syn after import
chip.set('option', 'flow', flow)
# end of flowgraph setup <docs reference>

# writes out the flowgraph
chip.write_flowgraph("heartbeat_flowgraph.svg")

# compiles and summarizes design info
chip.run()                                     # run compilation
chip.summary()                                 # print results summary
