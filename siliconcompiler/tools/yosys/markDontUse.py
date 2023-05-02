#!/usr/bin/env python3
# Based on https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/84545863573a90bca3612298361adb35bf39e692/flow/util/markDontUse.py

import re
import gzip
import argparse  # argument parsing


def processLibertyFile(input_file, output_file, dont_use, quiet=False):
    # Convert * wildcards to regex wildcards
    patternList = [du.replace('*', '.*') for du in dont_use]

    # Read input file
    if not quiet:
        print("Opening file for replace:", input_file)
    if input_file.endswith(".gz") or input_file.endswith(".GZ"):
        f = gzip.open(input_file, 'rt', encoding="utf-8")
    else:
        f = open(input_file, encoding="utf-8")
    content = f.read().encode("ascii", "ignore").decode("ascii")
    f.close()

    # Pattern to match a cell header
    cell_pattern = r"[\"]*|[\"]*"
    pattern = r"(^\s*cell\s*\(\s*([\"]*" + cell_pattern.join(patternList) + r"[\"]*)\)\s*\{)"

    # print(pattern)
    replace = r"\1\n    dont_use : true;"
    content, count = re.subn(pattern, replace, content, 0, re.M)
    if not quiet:
        print("Marked", count, "cells as dont_use")

    # Yosys-abc throws an error if original_pin is found within the liberty file.
    # removing
    pattern = r"(.*original_pin.*)"
    replace = r"/* \1 */;"
    content, count = re.subn(pattern, replace, content)
    if not quiet:
        print("Commented", count, "lines containing \"original_pin\"")

    # Yosys, does not like properties that start with : !, without quotes
    pattern = r":\s+(!.*)\s+;"
    replace = r': "\1" ;'
    content, count = re.subn(pattern, replace, content)
    if not quiet:
        print("Replaced malformed functions", count)

    # Yosys-abc throws an error if the units are specified in 0.001pf, instead of 1ff
    pattern = r"capacitive_load_unit\s+\(0.001,pf\);"
    replace = "capacitive_load_unit (1,ff);"
    content, count = re.subn(pattern, replace, content)
    if not quiet:
        print("Replaced capacitive load", count)

    # Write output file
    if not quiet:
        print("Writing replaced file:", output_file)
    f = open(output_file, "w")
    f.write(content)
    f.close()


if __name__ == "__main__":
    # Parse and validate arguments
    # ==============================================================================
    parser = argparse.ArgumentParser(
        description='Replaces occurrences of cells in def or verilog files')
    parser.add_argument('--patterns', '-p', required=True,
                        help='List of search patterns')
    parser.add_argument('--inputFile', '-i', required=True,
                        help='Input File')
    parser.add_argument('--outputFile', '-o', required=True,
                        help='Output File')
    args = parser.parse_args()

    processLibertyFile(args.inputFile, args.outputFile, args.patterns)
