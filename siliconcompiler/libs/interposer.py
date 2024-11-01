import siliconcompiler
from lambdapdk.interposer.libs.bumps import setup


#########################
if __name__ == "__main__":
    lib = setup(siliconcompiler.Chip('<lib>'))
    lib.write_manifest(f'{lib.top()}.json')
