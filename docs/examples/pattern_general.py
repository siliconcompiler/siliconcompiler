import siliconcompiler                       # import python package
syn_np = 4
chip = siliconcompiler.Chip()
chip.node('import', 'surelog')
chip.node('syn', 'yosys', n=syn_np)
chip.node('synmin', 'minimum')
chip.node('floorplan', 'openroad')
chip.node('lec', 'yosys')
for i in range(syn_np):
    chip.edge('import', 'syn', head_index=i)
    chip.edge('syn', 'synmin', tail_index=i)
chip.edge('synmin', 'floorplan')
chip.edge('floorplan', 'lec')
chip.edge('import', 'lec')
chip.write_flowgraph("pattern_general.png")
