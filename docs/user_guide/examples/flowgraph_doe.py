# import python package and create chip object
import siliconcompiler
chip = siliconcompiler.Chip('doe_demo')

# set synthesis strategies
syn_strategies = ['DELAY0', 'DELAY1', 'DELAY2', 'DELAY3', 'AREA0', 'AREA1', 'AREA2']

# define flowgraph name
flow = 'synparallel'

# create import node
chip.node(flow, 'import', 'surelog', 'import')

# create node for each syn strategy (first node called import and last node called synmin)
# and connect with edges
for index in range(len(syn_strategies)):
    chip.node(flow, 'syn', 'yosys', 'syn_asic', index=str(index))
    chip.edge(flow, 'import', 'syn', head_index=str(index))
    chip.edge(flow, 'syn', 'synmin', tail_index=str(index))
#    chip.set('tool', 'yosys', 'var', 'syn', str(index), 'strategy', syn_strategies[index])

    # set metric for each 
    for metric in ('cellarea', 'peakpower', 'standbypower'):
        chip.set('flowgraph', flow, 'syn', str(index), 'weight', metric, 1.0)

# create node for optimized (or minimum in this case) metric
chip.node(flow, 'synmin', 'builtin', 'minimum')


chip.set('option', 'flow', flow)
chip.write_flowgraph("flowgraph_doe.svg")
#chip.write_manifest("doe.json")
