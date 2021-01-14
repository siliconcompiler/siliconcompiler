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
    chip = sc.Chip()

    #Read environment variables
    chip.readenv()

    #Read in json files
    if(getattr(cmdargs,'sc_cfgfile') != None):
        for filename in getattr(cmdargs,'sc_cfgfile'):
            chip.readjson(filename)

    #Overide with command line arguments
    chip.readargs(cmdargs)

    #Lock chip configuration
    chip.lock()

    #Creating hashes for all sourced files
    chip.hash()
    
    #Printing out run-config
    chip.writejson(chip.get("sc_build") + "/sc_setup.json")

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
