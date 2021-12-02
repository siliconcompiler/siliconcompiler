import siliconcompiler
chip = siliconcompiler.Chip()

syn_strategies = ['DELAY0', 'DELAY1', 'DELAY2', 'DELAY3', 'AREA0', 'AREA1', 'AREA2']

chip.node('import', 'surelog')
for index in range(len(syn_strategies)):
    chip.node('syn', 'yosys', index=str(index))
    chip.edge('import', 'syn', head_index=str(index))
    chip.edge('syn', 'synmin', tail_index=str(index))
    chip.set('eda', 'yosys', 'syn', str(index), 'variable', 'strategy', syn_strategies[index])
    for metric in ('cellarea', 'peakpower', 'standbypower'):
        chip.set('flowgraph', 'syn', str(index), 'weight', metric, 1.0)
chip.node('synmin', 'minimum')
chip.write_flowgraph("flowgraph_doe.svg")
