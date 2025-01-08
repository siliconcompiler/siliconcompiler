from siliconcompiler.targets import asap7_demo
from siliconcompiler.targets import asic_demo
from siliconcompiler.targets import fpgaflow_demo
from siliconcompiler.targets import freepdk45_demo
from siliconcompiler.targets import gf180_demo
from siliconcompiler.targets import ihp130_demo
from siliconcompiler.targets import interposer_demo
from siliconcompiler.targets import skywater130_demo


def get_targets():
    '''
    Returns a dict of builtin targets
    '''
    return {
        module.__name__.split(".")[-1]: module for module in (
            asap7_demo,
            asic_demo,
            fpgaflow_demo,
            freepdk45_demo,
            gf180_demo,
            ihp130_demo,
            interposer_demo,
            skywater130_demo
        )
    }
