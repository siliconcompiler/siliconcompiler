###
# This is a docs example, referenced by its comments.
#
##

# import python package and create chip object
import siliconcompiler

# import pre-defined python packages for setting up tools used in flowgraph
from siliconcompiler.tools.surelog import parse
from siliconcompiler.tools.yosys import syn_asic
from siliconcompiler.tools.builtin import minimum

# create chip object
chip = siliconcompiler.Chip('doe_demo')

# set synthesis strategies <docs reference>
syn_strategies = ['DELAY0', 'DELAY1', 'DELAY2', 'DELAY3', 'AREA0', 'AREA1', 'AREA2']

# define flowgraph name
flow = 'synparallel'

# create import node
chip.node(flow, 'import', parse)

# create node for optimized (or minimum in this case) metric
chip.node(flow, 'synmin', minimum)

# create node for each syn strategy (first node called import and last node called synmin)
# and connect all synth nodes to both the first node and last node
for index in range(len(syn_strategies)):
    chip.node(flow, 'syn', syn_asic, index=str(index))
    chip.edge(flow, 'import', 'syn', head_index=str(index))
    chip.edge(flow, 'syn', 'synmin', tail_index=str(index))
    chip.set('tool', 'yosys', 'task', 'syn_asic', 'var', 'strategy', syn_strategies[index],
             step='syn', index=index)

    # set synthesis metrics that you want to optimize for
    for metric in ('cellarea', 'peakpower', 'standbypower'):
        chip.set('flowgraph', flow, 'syn', str(index), 'weight', metric, 1.0)


chip.set('option', 'flow', flow)
chip.write_flowgraph("flowgraph_doe.svg")
chip.write_manifest("doe.json")
