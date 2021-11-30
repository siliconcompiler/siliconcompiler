import siliconcompiler
chip = siliconcompiler.Chip()
chip.set('design', "hello_world")
chip.write_manifest("hello_world.json")
