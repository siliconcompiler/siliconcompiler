import siliconcompiler

#design to eda, eda to pdk
designs = 4
tools = 2
pdks = 4

# Status Quo problem
chip = siliconcompiler.Chip()
for i in range(designs):
    for j in range(tools):
        chip.add('flowgraph','tool', str(j), 'input', ('design',str(i)))

for j in range(tools):
    for k in range(pdks):
        chip.add('flowgraph','pdk', str(k), 'input', ('tool',str(j)))

chip.write_flowgraph('../_images/challenge_nsquared.png', fillcolor='#FFFFFF')

# SC option
chip = siliconcompiler.Chip()

#ir0
for i in range(designs):
    chip.add('flowgraph','sc0', '0', 'input', ('design',str(i)))

#eda
for i in range(tools):
    chip.add('flowgraph','tool', str(i), 'input', ('sc0','0'))
    chip.add('flowgraph','sc1', '0', 'input', ('tool',str(i)))

#pdk
for i in range(pdks):
    chip.add('flowgraph','pdk', str(i), 'input', ('sc1','0'))

chip.write_flowgraph('../_images/siliconcompiler_ir.png',fillcolor='#FFFFFF')
