# Copyright 2026 Silicon Compiler Authors. All Rights Reserved.
"""Utility to merge per-corner OpenRCX extraction rules into a single
multi-corner rules file.

PDKs (for example the lambdapdk gf180 PDK under
``lambdapdk/gf180/base/pex/openroad/``) ship OpenRCX extraction rules broken
out into one ``.rules`` file per process corner. Each of those files describes
a single corner and therefore contains exactly one ``DensityModel 0`` block::

    Extraction Rules for OpenRCX

    DIAGMODEL ON

    LayerCount 6
    DensityRate 1  0

    DensityModel 0
    ...
    END DensityModel 0

OpenRCX can also consume a single file that holds every corner, with one
``DensityModel <n>`` block per corner (for example the
``ext_pattern.rules.3corners`` file used by the OpenROAD rcx_v2 regression
flow)::

    LayerCount 6
    DensityRate 3  0 1 2

    DensityModel 0
    ...
    END DensityModel 0

    DensityModel 1
    ...
    END DensityModel 1

    DensityModel 2
    ...
    END DensityModel 2

This module reads the per-corner files (in the order they are given, which
defines the corner indices) and stitches them together into that combined
form. The body of each corner block is copied verbatim; only the
``DensityModel``/``END DensityModel`` markers are renumbered.
"""

import argparse
import re
import sys


# ``DensityModel 0`` (allow leading/trailing whitespace)
_DENSITY_MODEL_RE = re.compile(r"^\s*DensityModel\s+(\d+)\s*$")
_END_DENSITY_MODEL_RE = re.compile(r"^\s*END\s+DensityModel\s+(\d+)\s*$")
_LAYER_COUNT_RE = re.compile(r"^\s*LayerCount\s+(\d+)\s*$")


class RCXMergeError(Exception):
    """Raised when the input rules files cannot be merged."""


def _parse_rules(text, source):
    """Parse a single OpenRCX rules file.

    Returns a tuple of (layer_count, [density_model_blocks]) where each block is
    a list of lines beginning with ``DensityModel <n>`` and ending with
    ``END DensityModel <n>``.
    """
    lines = text.splitlines()

    layer_count = None
    for line in lines:
        match = _LAYER_COUNT_RE.match(line)
        if match:
            layer_count = int(match.group(1))
            break

    if layer_count is None:
        raise RCXMergeError(f"{source}: could not find a 'LayerCount' line")

    blocks = []
    current = None
    for line in lines:
        if current is None:
            if _DENSITY_MODEL_RE.match(line):
                current = [line]
        else:
            current.append(line)
            if _END_DENSITY_MODEL_RE.match(line):
                blocks.append(current)
                current = None

    if current is not None:
        raise RCXMergeError(
            f"{source}: 'DensityModel' block is missing a matching "
            "'END DensityModel'")

    if not blocks:
        raise RCXMergeError(f"{source}: no 'DensityModel' blocks found")

    return layer_count, blocks


def _renumber_block(block, index):
    """Return a copy of a DensityModel block renumbered to ``index``."""
    renumbered = list(block)
    renumbered[0] = f"DensityModel {index}"
    renumbered[-1] = f"END DensityModel {index}"
    return renumbered


def merge_openrcx_rules(inputs, corner_names=None):
    """Merge per-corner OpenRCX rules into a single multi-corner rules string.

    Args:
        inputs (list of str): Paths to per-corner ``.rules`` files. The order
            defines the corner indices in the output (first file -> corner 0).
        corner_names (list of str, optional): Human readable corner names. When
            provided a documentation-only ``Corners`` line is emitted and the
            length must match ``inputs``.

    Returns:
        str: The contents of the merged multi-corner rules file.

    Raises:
        RCXMergeError: If the inputs are empty, disagree on ``LayerCount``, or
            are otherwise malformed.
    """
    if not inputs:
        raise RCXMergeError("at least one input rules file is required")

    if corner_names is not None and len(corner_names) != len(inputs):
        raise RCXMergeError(
            f"number of corner names ({len(corner_names)}) does not match "
            f"number of input files ({len(inputs)})")

    layer_count = None
    ordered_blocks = []
    for path in inputs:
        try:
            with open(path, "r") as fid:
                text = fid.read()
        except OSError as exc:
            raise RCXMergeError(f"unable to read '{path}': {exc}") from exc

        this_count, blocks = _parse_rules(text, path)

        if layer_count is None:
            layer_count = this_count
        elif this_count != layer_count:
            raise RCXMergeError(
                f"{path}: LayerCount {this_count} does not match {layer_count} "
                "from the first input; all corners must use the same stackup")

        if len(blocks) != 1:
            raise RCXMergeError(
                f"{path}: expected exactly one DensityModel block, found "
                f"{len(blocks)}")

        ordered_blocks.append(blocks[0])

    corner_count = len(ordered_blocks)
    indices = list(range(corner_count))

    out = []
    out.append("Extraction Rules for OpenRCX")
    out.append("")
    out.append("DIAGMODEL ON")
    out.append("")
    out.append(f"LayerCount {layer_count}")
    out.append(f"DensityRate {corner_count}  {' '.join(str(i) for i in indices)}")
    if corner_names is not None:
        out.append(f"Corners {corner_count} :  {' '.join(corner_names)}")
    out.append("")

    body_blocks = []
    for index, block in enumerate(ordered_blocks):
        body_blocks.append("\n".join(_renumber_block(block, index)))

    # ``out`` ends with a blank entry, so joining yields a single trailing
    # newline; add one more for the blank line before the first block. Corner
    # blocks are separated by a blank line, and the file ends with a newline.
    return "\n".join(out) + "\n" + "\n\n".join(body_blocks) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="Merge per-corner OpenRCX .rules files into a single "
                    "multi-corner rules file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""example:
  python -m siliconcompiler.tools.openroad.utils.rcx_merge \\
      -o ext_pattern.rules.3corners \\
      corner_min.rules corner_typ.rules corner_max.rules

The order of the input files defines the corner indices (DensityModel 0, 1,
...) in the merged output.""")
    parser.add_argument(
        "inputs",
        metavar="RULES",
        nargs="+",
        help="per-corner OpenRCX .rules files, in corner order")
    parser.add_argument(
        "-o", "--output",
        metavar="FILE",
        help="output file (defaults to stdout)")
    parser.add_argument(
        "-c", "--corner-names",
        metavar="NAME[,NAME...]",
        help="optional comma-separated corner names for a documentation-only "
             "'Corners' line; must match the number of inputs")

    args = parser.parse_args()

    corner_names = None
    if args.corner_names:
        corner_names = args.corner_names.split(",")

    try:
        merged = merge_openrcx_rules(args.inputs, corner_names=corner_names)
    except RCXMergeError as exc:
        parser.error(str(exc))

    if args.output:
        with open(args.output, "w") as fid:
            fid.write(merged)
    else:
        sys.stdout.write(merged)

    return 0


if __name__ == "__main__":
    sys.exit(main())
