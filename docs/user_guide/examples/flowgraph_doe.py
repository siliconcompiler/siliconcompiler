###
# This is a docs example, referenced by its comments.
#
##

# import python package and create chip object
from siliconcompiler import FlowgraphSchema

# import pre-defined python packages for setting up tools used in flowgraph
from siliconcompiler.tools.slang import elaborate
from siliconcompiler.tools.yosys import syn_asic
from siliconcompiler.tools.builtin import minimum

# create chip object
flow = FlowgraphSchema("synparallel")

# create elaboration node
flow.node('elaborate', elaborate.Elaborate())

# create node for optimized (or minimum in this case) metric
flow.node('synmin', minimum.MinimumTask())

# create node for each syn strategy (first node called import and last node called synmin)
# and connect all synth nodes to both the first node and last node
for index in range(7):
    # Create synthesis node
    flow.node('syn', syn_asic.ASICSynthesis(), index=str(index))

    # Connect synthesis node to elaborate
    flow.edge('elaborate', 'syn', head_index=str(index))

    # Connect synthesis node to minimization
    flow.edge('syn', 'synmin', tail_index=str(index))

    # set synthesis metrics that you want to optimize for
    for metric in ('cellarea', 'peakpower', 'standbypower'):
        flow.set('syn', str(index), 'weight', metric, 1.0)

flow.write_flowgraph("flowgraph_doe.svg")
