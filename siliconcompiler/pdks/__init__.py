from siliconcompiler.pdks import asap7
from siliconcompiler.pdks import freepdk45
from siliconcompiler.pdks import gf180
from siliconcompiler.pdks import ihp130
from siliconcompiler.pdks import interposer
from siliconcompiler.pdks import skywater130


def get_pdks():
    '''
    Returns a dict of builtin pdks
    '''
    return {
        module.__name__.split(".")[-1]: module for module in (
            asap7,
            freepdk45,
            gf180,
            ihp130,
            interposer,
            skywater130
        )
    }
