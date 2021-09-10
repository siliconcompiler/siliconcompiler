# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import re
import os
import sys

################################################################
def schema_path(filename):
    ''' Resolves file paths using SCPATH and resolve environment
    variables starting with $
    '''

    if filename==None:
        return None

    #Resolve absolute path usign SCPATH
    #list is read left to right
    scpaths = str(os.environ['SCPATH']).split(':')
    for searchdir in scpaths:
        abspath = searchdir + "/" + filename
        if os.path.exists(abspath):
            filename = abspath
            break
    #Replace $ Variables
    varmatch = re.match(r'^\$(\w+)(.*)', filename)
    if varmatch:
        var = varmatch.group(1)
        varpath = os.getenv(var)
        if varpath is None:
            print("ERROR: Missing environment variable:", var)
            sys.exit()
            relpath = varmatch.group(2)
            filename = varpath + relpath

    return filename
################################################################
