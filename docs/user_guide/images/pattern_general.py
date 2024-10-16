import siliconcompiler                       # import python package
from siliconcompiler.tools.surelog import parse
from siliconcompiler.tools.yosys import syn_asic, lec
from siliconcompiler.tools.builtin import minimum
from siliconcompiler.tools.openroad import init_floorplan
syn_np = 4
chip = siliconcompiler.Chip('pattern_general')
flow = 'pattern_general_flow'

# nodes
chip.node(flow, 'import', parse)
for i in range(syn_np):
    chip.node(flow, 'syn', syn_asic, index=i)
chip.node(flow, 'synmin', minimum)
chip.node(flow, 'floorplan', init_floorplan)
chip.node(flow, 'lec', lec)

# edges
for i in range(syn_np):
    chip.edge(flow, 'import', 'syn', head_index=i)
    chip.edge(flow, 'syn', 'synmin', tail_index=i)
chip.edge(flow, 'synmin', 'floorplan')
chip.edge(flow, 'floorplan', 'lec')
chip.edge(flow, 'import', 'lec')
chip.write_flowgraph("../_images/pattern_general.png", flow)
