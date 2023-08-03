import siliconcompiler

# design to eda, eda to pdk
designers = 4
firewall = 1
pdks = 4

# NDA firewall
chip = siliconcompiler.Chip('challenge_nda')

# create fake tool and tasks
task = 'faketask'
open = 'open'
closed = 'closed'
chip.set('tool', open, 'task', open, 'var', 'fakevar', 'fakeval')
chip.set('tool', closed, 'task', closed, 'var', 'fakevar', 'fakeval')

flow = 'challenge_nda_flow'
for i in range(designers):
    chip.node(flow, 'designer', open + '.' + task, index=i)
    chip.edge(flow, 'designer', 'proxy', tail_index=i, head_index=0)

for i in range(pdks):
    chip.node(flow, 'pdk', closed + '.' + task, index=i)
    chip.edge(flow, 'proxy', 'pdk', tail_index=0, head_index=i)

chip.write_flowgraph('../_images/siliconcompiler_proxy.png', fillcolor='#FFFFFF', flow=flow)
