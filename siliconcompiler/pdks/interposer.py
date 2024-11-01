import siliconcompiler
from lambdapdk.interposer import setup


#########################
if __name__ == "__main__":
    pdk = setup(siliconcompiler.Chip('<lib>'))
    pdk.write_manifest(f'{pdk.top()}.json')
