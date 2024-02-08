import siliconcompiler
from lambdapdk.sky130.libs.sky130io import setup


#########################
if __name__ == "__main__":
    lib = setup(siliconcompiler.Chip('<lib>'))
    lib.write_manifest(f'{lib.top()}.json')
