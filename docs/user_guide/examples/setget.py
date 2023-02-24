import siliconcompiler
chip = siliconcompiler.Chip('hello_world')
chip.set('input', 'rtl', 'verilog', 'hello_world.v')
print(chip.get('input', 'rtl', 'verilog'))
