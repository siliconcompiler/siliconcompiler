from siliconcompiler import ASICProject

from .asap7_demo import setup as asap7
from .freepdk45_demo import setup as freepdk45
from .gf180_demo import setup as gf180
from .ihp130_demo import setup as ihp130
from .skywater130_demo import setup as sky130


def asic_target(proj: ASICProject, pdk: str = "asap7"):
    if pdk == "asap7":
        proj.load_target(asap7)
    elif pdk == "freepdk45":
        proj.load_target(freepdk45)
    elif pdk == "gf180":
        proj.load_target(gf180)
    elif pdk == "ihp130":
        proj.load_target(ihp130)
    elif pdk == "sky130":
        proj.load_target(sky130)
    else:
        raise ValueError(f"{pdk} not supported")
