import siliconcompiler
chip = siliconcompiler.Chip('hello_world')
chip.set('input', 'verilog', 'hello_world.v')
print(chip.get('input', 'verilog'))
