#!/usr/bin/env python3
# Based on https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/84545863573a90bca3612298361adb35bf39e692/flow/util/markDontUse.py  # noqa E501

import re
import gzip
import argparse  # argument parsing
import fnmatch


def processLibertyFile(input_file, dont_use=None, logger=None):
    # Read input file
    if logger:
        logger.info(f"Opening file for replace: {input_file}")
    if input_file.endswith(".gz") or input_file.endswith(".GZ"):
        f = gzip.open(input_file, 'rt', encoding="utf-8")
    else:
        f = open(input_file, encoding="utf-8")
    content = f.read().encode("ascii", "ignore").decode("ascii")
    f.close()

    if dont_use:
        # Pattern to match a cell header
        patternList = [re.compile(fnmatch.translate(du)) for du in dont_use]

        content_dont_use = ""
        re_cell_line = re.compile(r"^\s*cell\s*\(\s*[\"]?(\w+)[\"]?\)\s*\{")
        count = 0
        for line in content.splitlines():
            content_dont_use += line + "\n"
            cell_match = re_cell_line.match(line)
            if cell_match:
                for du in patternList:
                    if du.match(cell_match.group(1)):
                        if logger:
                            logger.info(f'  Marking {cell_match.group(1)} as dont_use')
                        content_dont_use += "    dont_use : true;\n"
                        count += 1
                        break
        content = content_dont_use
        if logger:
            logger.info(f"Marked {count} cells as dont_use")

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

    processLibertyFile(args.inputFile, args.outputFile, args.patterns)
