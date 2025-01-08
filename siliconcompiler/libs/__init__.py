from siliconcompiler.libs import asap7sc7p5t
from siliconcompiler.libs import gf180mcu
from siliconcompiler.libs import interposer
from siliconcompiler.libs import nangate45
from siliconcompiler.libs import sg13g2_stdcell
from siliconcompiler.libs import sky130hd
from siliconcompiler.libs import sky130io


def get_libs():
    '''
    Returns a dict of builtin libraries
    '''
    return {
        module.__name__.split(".")[-1]: module for module in (
            asap7sc7p5t,
            gf180mcu,
            interposer,
            nangate45,
            sg13g2_stdcell,
            sky130hd,
            sky130io
        )
    }
