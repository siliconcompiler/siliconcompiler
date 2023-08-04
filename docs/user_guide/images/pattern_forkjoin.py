import siliconcompiler                        # import python package
from siliconcompiler.tools.surelog import parse
from siliconcompiler.tools.yosys import syn_asic
from siliconcompiler.tools.builtin import minimum
syn_np = 4
chip = siliconcompiler.Chip('pattern_forkjoin')                 # create chip object
flow = 'pattern_forkjoin_flow'
chip.node(flow, 'import', parse)                # create import task
chip.node(flow, 'synmin', minimum)                # select minimum
for i in range(syn_np):
    chip.node(flow, 'syn', syn_asic, index=i)        # create 4 syn tasks
    chip.edge(flow, 'import', 'syn', head_index=i)  # broadcast
    chip.edge(flow, 'syn', 'synmin', tail_index=i)  # merge
chip.write_flowgraph("../_images/pattern_forkjoin.png", flow)  # write out flowgraph picture
