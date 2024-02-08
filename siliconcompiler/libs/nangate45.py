import siliconcompiler
from lambdapdk.freepdk45.libs.nangate45 import setup


#########################
if __name__ == "__main__":
    lib = setup(siliconcompiler.Chip('<lib>'))
    lib.write_manifest(f'{lib.top()}.json')
