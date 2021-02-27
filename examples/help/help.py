
import siliconcompiler
from siliconcompiler.schema import schema
from siliconcompiler.schema import schema_help

# Create instance of Chip class
chip = siliconcompiler.Chip()

#Print out help for simpl variables
for key in chip.cfg.keys():
    if 'help' in chip.cfg[key].keys():
        print("\n")
        print(schema_help(chip.cfg[key],mode="help", format="md"))

chip.writecfg("help.json")
