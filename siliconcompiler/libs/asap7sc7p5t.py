import siliconcompiler
from lambdapdk.asap7.libs.asap7sc7p5t import setup


#########################
if __name__ == "__main__":
    for lib in setup(siliconcompiler.Chip('<lib>')):
        lib.write_manifest(f'{lib.top()}.json')
