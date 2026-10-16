# Copyright 2026 Silicon Compiler Authors. All Rights Reserved.
"""Convert the liberty files of a standard cell library to binary liberty.

OpenROAD loads binary liberty (``.blib``) faster than the text format. This
utility runs :class:`.LibertyBinaryTask` on a library, converting the liberty
files in its corner filesets for one delay model, and can copy the results into
an install directory. Added to the fileset its source came from, a ``.blib``
file is read by OpenROAD in place of that fileset's text liberty.

Command line::

    python -m siliconcompiler.tools.openroad.utils.liberty_binary \\
        lambdapdk.freepdk45.libs.nangate45:Nangate45 -o nangate45_blib

Python::

    from lambdapdk.freepdk45.libs.nangate45 import Nangate45
    from siliconcompiler.tools.openroad.utils import liberty_binary
    liberty_binary.build_liberty_binary(Nangate45(), installpath="nangate45_blib")
"""

import argparse
import importlib
import os
import sys

from typing import Optional

from siliconcompiler import ASIC, Design, Flowgraph, StdCellLibrary
from siliconcompiler.tools.openroad.liberty_binary import LibertyBinaryTask


def build_liberty_binary(library: StdCellLibrary,
                         delaymodel: str = "nldm",
                         installpath: Optional[str] = None,
                         compress: bool = True) -> ASIC:
    """
    Converts the liberty files of a library to binary liberty.

    Runs :class:`.LibertyBinaryTask` in a project of its own, with ``library`` as
    the main library and its PDK.

    Args:
        library (StdCellLibrary): The library to convert.
        delaymodel (str, optional): Delay model whose liberty files are converted,
            ``nldm`` or ``ccs``.
        installpath (str, optional): Directory to also copy the binary liberty
            files into, created if missing.
        compress (bool, optional): Whether to gzip the binary liberty files.

    Returns:
        ASIC: The completed job, as returned by :meth:`.Project.run`.
    """
    design = Design(f"liberty-binary-{library.name}")
    design.set_topmodule(library.name, fileset="library")

    project = ASIC(design)
    project.add_fileset("library")
    project.set_mainlib(library)
    project.set_pdk(library.get("asic", "pdk"))
    project.set_asic_delaymodel(delaymodel)

    flow = Flowgraph("liberty_binary")
    flow.node("convert", LibertyBinaryTask())
    project.set_flow(flow)

    task = LibertyBinaryTask.find_task(project)
    task.set_openroad_compress(compress)
    if installpath:
        task.set_openroad_installpath(os.path.abspath(installpath))

    return project.run()


def _load_library(spec: str) -> StdCellLibrary:
    """Instantiate the library class a ``module:Class`` or ``module.Class`` path names."""
    if ":" in spec:
        modname, name = spec.split(":", 1)
    else:
        modname, _, name = spec.rpartition(".")
    try:
        cls = getattr(importlib.import_module(modname), name)
    except (ImportError, AttributeError, ValueError) as exc:
        raise ValueError(f"could not resolve library '{spec}': {exc}") from exc

    if not (isinstance(cls, type) and issubclass(cls, StdCellLibrary)):
        raise ValueError(f"'{spec}' is not a standard cell library class")
    return cls()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Convert the liberty files of a standard cell library to OpenROAD "
                    "binary liberty (.blib).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""examples:
  # convert the nldm liberty files and copy the .blib.gz files into ./nangate45_blib
  python -m siliconcompiler.tools.openroad.utils.liberty_binary \\
      lambdapdk.freepdk45.libs.nangate45:Nangate45 -o nangate45_blib

  # convert the ccs liberty files, uncompressed
  python -m siliconcompiler.tools.openroad.utils.liberty_binary \\
      my_pkg.libs:MyLibrary --delaymodel ccs --no-compress""")
    parser.add_argument(
        "library",
        help="library class: a 'module:Class' or 'module.Class' path")
    parser.add_argument(
        "--delaymodel", choices=("nldm", "ccs"), default="nldm",
        help="delay model whose liberty files are converted (default: nldm)")
    parser.add_argument(
        "-o", "--installpath", metavar="DIR",
        help="directory to also copy the binary liberty files into; they are always "
             "in the job's outputs")
    parser.add_argument(
        "--no-compress", dest="compress", action="store_false",
        help="write .blib files instead of gzipped .blib.gz")
    args = parser.parse_args(argv)

    try:
        library = _load_library(args.library)
    except ValueError as exc:
        parser.error(str(exc))

    build_liberty_binary(library, delaymodel=args.delaymodel,
                         installpath=args.installpath, compress=args.compress)
    return 0


if __name__ == "__main__":
    sys.exit(main())
