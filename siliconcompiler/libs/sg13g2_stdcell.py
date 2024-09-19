import siliconcompiler
from lambdapdk.ihp130.libs.sg13g2_stdcell import setup


#########################
if __name__ == "__main__":
    lib = setup(siliconcompiler.Chip('<lib>'))
    lib.write_manifest(f'{lib.top()}.json')
