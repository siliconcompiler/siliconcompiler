import os
import sys
from pathlib import Path

from siliconcompiler import Project
from lambdapdk.asap7 import ASAP7PDK
from lambdapdk.ihp130 import IHP130PDK
# from logiklib.demo.K4_N8_6x6 import K4_N8_6x6
# from logiklib.demo.K6_N8_3x3 import K6_N8_3x3
# from logiklib.demo.K6_N8_12x12_BD import K6_N8_12x12_BD
# from logiklib.demo.K6_N8_28x28_BD import K6_N8_28x28_BD


if __name__ == "__main__":
    proj = Project("cache")

    proj.set('option', 'cachedir', Path(os.getcwd()) / '.sc' / 'cache')

    proj.add_dep(ASAP7PDK())
    proj.add_dep(IHP130PDK())

    proj.check_filepaths([("option", "builddir")])

    sys.exit(0)
