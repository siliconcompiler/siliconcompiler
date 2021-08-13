import siliconcompiler

a = siliconcompiler.Chip()
design = 'top'

a.set('design', design)
a.add('hier', design, 'a', 'build', 'true')
a.add('hier', design, 'b', 'build', 'true')
a.add('hier', design, 'c', 'build', 'true')
a.add('hier', 'c', 'd', 'build', 'true')

a.writegraph('hier', 'hier.dot')

#to view file
#dot -Tpng hier.dot > hier.png ; gimp hier.png
