from .asap7_demo import setup as asap7_demo
from .freepdk45_demo import setup as freepdk45_demo
from .gf180_demo import setup as gf180_demo
from .ihp130_demo import setup as ihp130_demo
from .skywater130_demo import setup as skywater130_demo

from siliconcompiler import ASICProject


def asic_target(proj: ASICProject, pdk: str = None):
    if pdk == "asap7":
        asap7_demo(proj)
    elif pdk == "freepdk45":
        freepdk45_demo(proj)
    elif pdk == "gf180":
        gf180_demo(proj)
    elif pdk == "ihp130":
        ihp130_demo(proj)
    elif pdk == "skywater130":
        skywater130_demo(proj)
    else:
        raise ValueError(f"pdk not supported: {pdk}")
