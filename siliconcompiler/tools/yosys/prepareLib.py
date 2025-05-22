#!/usr/bin/env python3
# Based on https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/84545863573a90bca3612298361adb35bf39e692/flow/util/markDontUse.py  # noqa E501

import re
import gzip
import argparse  # argument parsing


def process_liberty_file(input_file, logger=None):
    # Read input file
    if logger:
        logger.info(f"Opening file for replace: {input_file}")
    if input_file.endswith(".gz") or input_file.endswith(".GZ"):
        f = gzip.open(input_file, 'rt', encoding="utf-8")
    else:
        f = open(input_file, encoding="utf-8")
    content = f.read().encode("ascii", "ignore").decode("ascii")
    f.close()

    # Yosys-abc throws an error if original_pin is found within the liberty file.
    # removing
    pattern = r"(.*original_pin.*)"
    replace = r"/* \1 */;"
    content, count = re.subn(pattern, replace, content)
    if logger:
        logger.info(f"Commented {count} lines containing \"original_pin\"")

    # Yosys, does not like properties that start with : !, without quotes
    pattern = r":\s+(!.*)\s+;"
    replace = r': "\1" ;'
    content, count = re.subn(pattern, replace, content)
    if logger:
        logger.info(f"Replaced malformed functions {count}")

    # Yosys-abc throws an error if the units are specified in 0.001pf, instead of 1ff
    pattern = r"capacitive_load_unit\s+\(0.001,pf\);"
    replace = "capacitive_load_unit (1,ff);"
    content, count = re.subn(pattern, replace, content)
    if logger:
        logger.info(f"Replaced capacitive load {count}")

    # Return new text
    return content


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

    process_liberty_file(args.inputFile, args.outputFile, args.patterns)
