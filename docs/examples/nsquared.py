import siliconcompiler
chip = siliconcompiler.Chip()



#design to eda, eda to pdk
designs=8
eda=4
pdks=8

for i in range(designs):
    chip.add('flowgraph','design'+str(i),'0', 'tool', 'manual')
    for j in range(eda):
        chip.add('flowgraph','eda'+str(j),'0', 'input', 'design'+str(i)+'0')

for j in range(eda):
    for k in range(pdks):
        chip.add('flowgraph','pdk'+str(k),'0', 'input', 'eda'+str(j)+'0')

chip.write_flowgraph('nsquared.png',
                     fillcolor='#1c4587', fontcolor='#f1c232',
                     border=False, landscape=True)
