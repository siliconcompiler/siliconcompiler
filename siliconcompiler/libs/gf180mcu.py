import siliconcompiler
from lambdapdk.gf180.libs.gf180mcu import setup


#########################
if __name__ == "__main__":
    lib = setup(siliconcompiler.Chip('<lib>'))
    lib.write_manifest(f'{lib.top()}.json')
