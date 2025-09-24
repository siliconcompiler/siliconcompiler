from . import asap7_demo
from . import freepdk45_demo
from . import gf180_demo
from . import ihp130_demo
from . import skywater130_demo

from siliconcompiler import ASICProject


def asic_target(proj: ASICProject, pdk: str = None):
    if pdk == "asap7":
        asap7_demo.setup(proj)
    elif pdk == "freepdk45":
        freepdk45_demo.setup(proj)
    elif pdk == "gf180":
        gf180_demo.setup(proj)
    elif pdk == "ihp130":
        ihp130_demo.setup(proj)
    elif pdk == "skywater130":
        skywater130_demo.setup(proj)
    else:
        raise ValueError(f"pdk not supported: {pdk}")
