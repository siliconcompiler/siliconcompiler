import os
import sys
from pathlib import Path

from siliconcompiler import Project
from lambdapdk.asap7 import ASAP7PDK
from lambdapdk.ihp130 import IHP130PDK


if __name__ == "__main__":
    proj = Project("cache")

    proj.set('option', 'cachedir', Path(os.getcwd()) / '.sc' / 'cache')

    proj.add_dep(ASAP7PDK())
    proj.add_dep(IHP130PDK())

    proj.check_filepaths([("option", "builddir")])

    sys.exit(0)
