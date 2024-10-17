import siliconcompiler                    # import python package
from siliconcompiler.tools.surelog import parse
from siliconcompiler.tools.builtin import minimum
from siliconcompiler.tools.yosys import syn_asic
from siliconcompiler.tools.openroad import init_floorplan, global_placement, global_route
pipes = 4
chip = siliconcompiler.Chip('pattern_pipeline')
flow = 'pattern_pipeline_flow'

# Tasks
chip.node(flow, 'import', parse)
chip.node(flow, 'merge', minimum)
for i in range(pipes):
    chip.node(flow, 'syn', syn_asic, index=i)
    chip.node(flow, 'floorplan', init_floorplan, index=i)
    chip.node(flow, 'place', global_placement, index=i)
    chip.node(flow, 'route', global_route, index=i)

# Connections
for i in range(pipes):
    chip.edge(flow, 'import', 'syn', head_index=i)
    chip.edge(flow, 'syn', 'floorplan', tail_index=i, head_index=i)
    chip.edge(flow, 'floorplan', 'place', tail_index=i, head_index=i)
    chip.edge(flow, 'place', 'route', tail_index=i, head_index=i)
    chip.edge(flow, 'route', 'merge', tail_index=i)

chip.write_flowgraph("../_images/pattern_pipeline.png", flow)
