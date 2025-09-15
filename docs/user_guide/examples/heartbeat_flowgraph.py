###
# This is a docs example, referenced by its comments.
#
##

from siliconcompiler import Flowgraph

# import pre-defined python packages for setting up tools used in flowgraph
from siliconcompiler.tools.slang import elaborate
from siliconcompiler.tools.yosys import syn_asic

# modify flowgraph:
# start of flowgraph setup <docs reference>
flow = Flowgraph('synonlyflow')
flow.node('elaborate', elaborate.Elaborate())               # use surelog for import
flow.node('syn', syn_asic.ASICSynthesis())               # use yosys for synthesis
flow.edge('elaborate', 'syn')               # perform syn after import
# end of flowgraph setup <docs reference>

# writes out the flowgraph
flow.write_flowgraph("heartbeat_flowgraph.svg")
