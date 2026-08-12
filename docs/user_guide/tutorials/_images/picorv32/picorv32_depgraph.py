"""Fileset dependency graph for the picorv32 tutorial.

Rendered into ``picorv32_ram.rst`` by the ``scdepgraph`` directive.

The design is **not** redefined here. It is imported from
``examples/picorv32/make.py``, the same file the page shows through
``literalinclude``, so the picture cannot drift away from the example.

What this file adds is the part the example has no reason to provide: a project
assembled but not run, and stopped before the target is applied. Applying the
target is correct for a build and wrong for this diagram -- it pulls in the PDK,
the standard cell library and every macro library the target registers, which
comes out around 2600pt wide and buries the fileset composition that section of
the page is about.
"""

import importlib.util
import os

from siliconcompiler import ASIC

# Load the example under a private name so importing it cannot collide with, or
# be satisfied from, another example's equally generic ``make``.
#
# Two levels up is the tutorials directory, which is where the ``examples``
# symlink to the top-level ``examples/`` lives. Going through that symlink rather
# than up to the repository root keeps this working whenever the docs build from
# a checkout, including when the package itself is installed elsewhere.
_MAKE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                     "examples", "picorv32", "make.py")
_spec = importlib.util.spec_from_file_location("_picorv32_make", _MAKE)
_make = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_make)


def project(fileset: str, pdk: str = "freepdk45") -> ASIC:
    """Assemble the picorv32 project's design side for one fileset."""
    proj = ASIC()
    proj.set_design(_make.PicoRV32Design())
    proj.add_fileset(fileset)
    proj.add_fileset(f"sdc.{pdk}")
    return proj
