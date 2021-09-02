import siliconcompiler
import matplotlib.pyplot as plt

# datawidths to check
datawidths = [8,16,32,64]
source ='third_party/designs/oh/stdlib/hdl/oh_add.v'
design = 'oh_add'

# Gather Data
area = []
for n in datawidths:
    param = "N="+str(n)
    chip = siliconcompiler.Chip(loglevel="INFO")
    chip.target('freepdk45_asicflow')
    chip.add('source', source)
    chip.set('design', design)
    chip.set('quiet', True)
    chip.set('relax', True)
    chip.set('stop','syn')
    chip.set('param','N',str(n))
    chip.run()
    area.append(chip.get('metric','syn', 'real', 'area_cells'))

# Plot Data
fig, ax = plt.subplots(1, 1)

plt.plot(datawidths, area)
plt.show()
