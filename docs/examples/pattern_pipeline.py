import siliconcompiler                    # import python package
pipes = 4
chip = siliconcompiler.Chip()

# Tasks
chip.node('import', 'surelog')
chip.node('syn', 'yosys', n=pipes)
chip.node('floorplan', 'openroad', n=pipes)
chip.node('place', 'openroad', n=pipes)
chip.node('route', 'openroad', n=pipes)
chip.node('merge', 'minimum')

# Connections
for i in range(pipes):
    chip.edge('import', 'syn', head_index=i)
    chip.edge('syn', 'floorplan', tail_index=i, head_index=i)
    chip.edge('floorplan', 'place', tail_index=i, head_index=i)
    chip.edge('place', 'route', tail_index=i, head_index=i)
    chip.edge('route', 'merge', tail_index=i)

chip.write_flowgraph("pattern_pipeline.png")
