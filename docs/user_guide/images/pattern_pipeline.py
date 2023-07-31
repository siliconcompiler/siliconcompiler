import siliconcompiler                    # import python package
pipes = 4
chip = siliconcompiler.Chip()

# Tasks
chip.node('import', 'surelog')
chip.node('merge', 'minimum')
for i in range(pipes):
    chip.node('syn', 'yosys', index=i)
    chip.node('floorplan', 'openroad', index=i)
    chip.node('place', 'openroad', index=i)
    chip.node('route', 'openroad', index=i)

# Connections
for i in range(pipes):
    chip.edge('import', 'syn', head_index=i)
    chip.edge('syn', 'floorplan', tail_index=i, head_index=i)
    chip.edge('floorplan', 'place', tail_index=i, head_index=i)
    chip.edge('place', 'route', tail_index=i, head_index=i)
    chip.edge('route', 'merge', tail_index=i)

chip.write_flowgraph("../_images/pattern_pipeline.png")
