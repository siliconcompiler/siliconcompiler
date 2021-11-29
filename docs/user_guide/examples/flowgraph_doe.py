import siliconcompiler
chip = siliconcompiler.Chip()

chip.node('import', 'surelog')
for index in range(10):
    chip.node('syn', 'yosys', index=str(index))
    chip.edge('import', 'syn', head_index=str(index))
    chip.edge('syn', 'synmin', tail_index=str(index))
    for metric in ('cellarea', 'peakpower', 'standbypower'):
        chip.set('flowgraph', 'syn', str(index), 'weight', metric, 1.0)
chip.node('synmin', 'minimum')
chip.write_flowgraph("flowgraph_doe.svg")
