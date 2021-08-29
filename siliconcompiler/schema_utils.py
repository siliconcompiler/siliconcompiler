# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import re
import os
import sys

##############################################################
def schema_switchparse (switch_field):
    '''
    Routine for parsing the switch and example[0] and returns
    an argument list. The following schema assumptions are made:
    * switches start with + or -
    * The +case+ case is a verilog legacy case (no spacing)
    * The ' character is note used in any args/values

    '''

    # removing doc prefix help
    example = re.sub(r'^cli:\s\+','', switch_field)
    # removing all quotes
    example = re.sub('\'','',example)
    # splitting into switch field and the rest
    plusmatch = re.match(r'\+(\w+)\+(.*)', example)
    if plusmatch:
        arglist = [plusmatch.group(1),
                   plusmatch.group(2)]
    else:
        arglist =  example.split(' ')

    return(arglist)

################################################################
def schema_typecheck(chip, cfg, leafkey, value):
    ''' Schema type checking
    '''

    # Check that value is list when type is scalar
    ok = True
    valuetype = type(value)
    if (not re.match(r'\[',cfg['type'])) & (valuetype==list):
        errormsg = "Value must be scalar."
        ok = False
        # Iterate over list
    else:
        # Create list for iteration
        if valuetype == list:
            valuelist = value
        else:
            valuelist = [value]
            # Make type python compatible
        cfgtype = re.sub(r'[\[\]]', '', cfg['type'])
        for item in valuelist:
            valuetype =  type(item)
            if (cfgtype != valuetype.__name__):
                tupletype = re.match(r'\([\w\,]+\)',cfgtype)
                #TODO: check tuples!
                if tupletype:
                    pass
                elif cfgtype == 'bool':
                    if not item in ['true', 'false']:
                        errormsg = "Valid boolean values are True/False/'true'/'false'"
                        ok = False
                elif cfgtype == 'file':
                    pass
                elif cfgtype == 'dir':
                    pass
                elif (cfgtype == 'float'):
                    try:
                        float(item)
                    except:
                        errormsg = "Type mismatch. Cannot cast item to float."
                        ok = False
                elif (cfgtype == 'int'):
                    try:
                        int(item)
                    except:
                        errormsg = "Type mismatch. Cannot cast item to int."
                        ok = False
                else:
                    errormsg = "Type mismach."
                    ok = False
    # Logger message
    if not ok:
        if type(value) == list:
            printvalue = ','.join(map(str, value))
        else:
            printvalue = str(value)
        errormsg = (errormsg +
                    " Key=" + str(leafkey) +
                    ", Expected Type=" + cfg['type'] +
                    ", Entered Type=" + valuetype.__name__ +
                    ", Value=" + printvalue)
        chip.logger.error("%s", errormsg)

    return ok

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
