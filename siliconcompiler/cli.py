# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

#Standard Modules
import sys
import logging

#Shorten siliconcompiler as sc
import siliconcompiler as sc

###########################
def main():

    #Command line interface
    cmdargs = sc.cmdline()

    #Create one (or many...) instances of Chip class
    chip = sc.Chip(cmdargs)

    #Creating hashes for all sourced files
    chip.hash()

    #Lock chip configuration
    chip.lock()
    
    #Printing out run-config
    chip.writecfg("sc_setup.json")

    #Compiler
    chip.run("import")
    chip.run("syn")
    chip.run("floorplan")
    chip.run("place")
    chip.run("cts")
    chip.run("route")
    chip.run("signoff")
    chip.run("export")
    
#########################
if __name__ == "__main__":    
    sys.exit(main())
