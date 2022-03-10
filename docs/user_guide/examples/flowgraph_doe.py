import siliconcompiler
chip = siliconcompiler.Chip()

syn_strategies = ['DELAY0', 'DELAY1', 'DELAY2', 'DELAY3', 'AREA0', 'AREA1', 'AREA2']

flow = 'synparallel'
chip.node(flow, 'import', 'surelog')
for index in range(len(syn_strategies)):
    chip.node(flow, 'syn', 'yosys', index=str(index))
    chip.edge(flow, 'import', 'syn', head_index=str(index))
    chip.edge(flow, 'syn', 'synmin', tail_index=str(index))
    chip.set('eda', 'yosys', 'variable', 'syn', str(index), 'strategy', syn_strategies[index])
    for metric in ('cellarea', 'peakpower', 'standbypower'):
        chip.set('flowgraph', flow, 'syn', str(index), 'weight', metric, 1.0)
chip.node(flow, 'synmin', 'minimum')
chip.set('flow', flow)
chip.write_flowgraph("flowgraph_doe.svg")
