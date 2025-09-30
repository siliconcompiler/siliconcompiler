from .asap7_demo import asap7_demo
from .freepdk45_demo import freepdk45_demo
from .gf180_demo import gf180_demo
from .ihp130_demo import ihp130_demo
from .skywater130_demo import skywater130_demo
from .interposer_demo import interposer_demo

from typing import Optional

from siliconcompiler import ASIC


def asic_target(proj: ASIC, pdk: Optional[str] = None):
    '''A factory function to configure an ASIC for a given PDK.

    This function acts as a dispatcher, calling the appropriate setup function
    (e.g., `skywater130_demo`, `asap7_demo`) based on the provided PDK name.
    It simplifies the process of targeting different silicon manufacturing
    processes by centralizing the selection logic.

    Args:
        proj (ASIC): The siliconcompiler project to configure.
        pdk (Optional[str]): The name of the Process Design Kit to target. Supported
            values are "asap7", "freepdk45", "gf180", "ihp130", and
            "skywater130".

    Raises:
        ValueError: If the provided `pdk` name is not supported.
    '''

    # Conditionally call the setup function that matches the requested PDK.
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
        # If the PDK is not in the list of supported targets, raise an error.
        raise ValueError(f"pdk not supported: {pdk}")


__all__ = [
    "asap7_demo",
    "freepdk45_demo",
    "gf180_demo",
    "ihp130_demo",
    "skywater130_demo",
    "interposer_demo"
]
