from . import asap7_demo
from . import freepdk45_demo
from . import gf180_demo
from . import ihp130_demo
from . import skywater130_demo

from siliconcompiler import ASICProject


def asic_target(proj: ASICProject, pdk: str = None):
    if pdk == "asap7":
        proj.load_target(asap7_demo.setup)
    elif pdk == "freepdk45":
        proj.load_target(freepdk45_demo.setup)
    elif pdk == "gf180":
        proj.load_target(gf180_demo.setup)
    elif pdk == "ihp130":
        proj.load_target(ihp130_demo.setup)
    elif pdk == "skywater130":
        proj.load_target(skywater130_demo.setup)
    else:
        raise ValueError(f"pdk not supported: {pdk}")
