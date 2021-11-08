import siliconcompiler

#design to eda, eda to pdk
designers = 4
firewall = 1
pdks = 4

# NDA firewall
chip = siliconcompiler.Chip()

for i in range(designers):
    chip.node('designer', 'open', index=i)
    chip.edge('designer', 'proxy', tail_index=i, head_index=0)

for i in range(pdks):
    chip.node('pdk', 'closed', index=i)
    chip.edge('proxy', 'pdk', tail_index=0, head_index=i)

chip.write_flowgraph('../_images/siliconcompiler_proxy.png',fillcolor='#FFFFFF')
