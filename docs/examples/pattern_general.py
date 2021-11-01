import siliconcompiler                       # import python package
syn_np = 4
chip = siliconcompiler.Chip()

# nodes
chip.node('import', 'surelog')
for i in range(syn_np):
    chip.node('syn', 'yosys', index=i)
chip.node('synmin', 'minimum')
chip.node('floorplan', 'openroad')
chip.node('lec', 'yosys')

# edges
for i in range(syn_np):
    chip.edge('import', 'syn', head_index=i)
    chip.edge('syn', 'synmin', tail_index=i)
chip.edge('synmin', 'floorplan')
chip.edge('floorplan', 'lec')
chip.edge('import', 'lec')
chip.write_flowgraph("pattern_general.png")
