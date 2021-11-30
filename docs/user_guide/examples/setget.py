import siliconcompiler
chip = siliconcompiler.Chip()
chip.set('design', "hello_world")
print(chip.get('design'))
