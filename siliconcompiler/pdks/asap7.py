import siliconcompiler
from lambdapdk.asap7 import setup


#########################
if __name__ == "__main__":
    pdk = setup(siliconcompiler.Chip('<pdk>'))
    pdk.write_manifest(f'{pdk.top()}.json')
