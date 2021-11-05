import siliconcompiler

#design to eda, eda to pdk
designs = 4
eda = 2
pdks = 4

# Status Quo problem
chip = siliconcompiler.Chip()
for i in range(designs):
    chip.set('flowgraph','design', str(i), 'tool', 'source')
    for j in range(eda):
        chip.add('flowgraph','eda', str(j), 'input', 'design'+str(i))

for j in range(eda):
    for k in range(pdks):
        chip.add('flowgraph','pdk', str(k), 'input', 'eda'+str(j))

chip.write_flowgraph('nsquared.png', fillcolor='#FFFFFF')

# SC option
chip = siliconcompiler.Chip()

#design

#ir0
for i in range(designs):
    chip.set('flowgraph','design', str(i), 'tool', 'source')
    chip.add('flowgraph','sc0', '0', 'input', 'design'+str(i))

#eda
for i in range(eda):
    chip.add('flowgraph','eda', str(i), 'input', 'sc00')
    chip.add('flowgraph','sc1', '0', 'input', 'eda'+str(i))

#pdk
for i in range(pdks):
    chip.add('flowgraph','pdk', str(i), 'input', 'sc10')

chip.write_flowgraph('sc_ir.png',fillcolor='#FFFFFF')
