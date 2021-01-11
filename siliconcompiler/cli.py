# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

#Standard Modules
import sys
import logging

#Shorten siliconcompiler as sc
import siliconcompiler as sc

#Silicon Compiler Modules
#from siliconcompiler.core import cli
#from siliconcompiler.core import run

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
    chip.writejson(chip.cfg['sc_build']['values'] + "/setup.json")
    chip.lock()
    
    #Printing out run-config
    chip.writejson(chip.cfg['sc_build']['values'] + "/setup.json")
    
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
