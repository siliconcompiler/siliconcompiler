import siliconcompiler

# Top level
topmodule = "liz"
top = siliconcompiler.Chip(topmodule, loglevel="DEBUG")
top.add('hier', topmodule, 'charlie', 'build', 'true')
top.add('hier', topmodule, 'andy', 'build', 'true')
top.add('hier', topmodule, 'annie', 'build', 'true')
top.add('hier', topmodule, 'eddie', 'build', 'true')
top.add('hier', 'charlie', 'willie', 'build', 'true')

# Child module
charlie = siliconcompiler.Chip("charlie", loglevel="DEBUG")

# Print out Hiearchy
top.writegraph('hier', 'hier.dot')

# Accessing 2nd module from top
print(top.get('design', chip=charlie))

#to view file
#dot -Tpng hier.dot > hier.png ; gimp hier.png
