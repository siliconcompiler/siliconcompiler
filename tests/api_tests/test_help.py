# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import siliconcompiler

def main():
    progname = "sc-echo"
    chip = siliconcompiler.Chip(loglevel="INFO")
    allkeys = chip.getkeys()
    for key in allkeys:
        print(chip.help(*key))

#########################
if __name__ == "__main__":
    sys.exit(main())
