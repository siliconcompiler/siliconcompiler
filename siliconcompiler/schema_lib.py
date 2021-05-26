def schema_lib (lib):

    ##############
    # PROPERTIES
    ##############
    
    cell['width'] = {
        'type' : 'str',
        'defvalue' : ['0.0'],
        'short_help' : "Cell Width",
        'param_help' : "'cell' 'width' <str>",
        'example': ["lib.set('nand2_1x', 'width', '100')"],
        'help' : """
        Cell width specified in nanometeres
        """
    }
    
    cell['height'] = {
        'type' : 'str',
        'defvalue' : ['0.0'],
        'short_help' : "Cell Height",
        'param_help' : "'cell' 'height' <str>",
        'example': ["lib.set('nand2_1x', 'height', '400')"],
        'help' : """
        Cell height specified in nanometers
        """
    }

    cell['function'] = {
        'type' : 'str',
        'defvalue' : [],
        'short_help' : "Cell Function",
        'param_help' : "'cell' 'function' <str>",
        'example': ["lib.set('nand2_1x', 'function', '~(a&b)"],
        'help' : """
        Cell function
        """
    }

    ########################
    # INTERFACE
    ########################
    
    pin['default']['dir'] = {
        'type' : 'str',
        'defvalue' : [],
        'short_help' : "Pin Direction",
        'param_help' : "cellname 'pin' name 'dir' <str>",
        'help' : """
        Specifies pin direction (input, output, inout)
        """
    }
    
    pin['default']['range'] = {
        'type' : 'str',
        'defvalue' : ['0:0'],
        'short_help' : "Pin Range",
        'param_help' : "cellname 'pin' name 'range' <str>",
        'help' : """
        Specifies pin direction (input, output, inout)
        """
    }
    
    pin['default']['type'] = {
        'type' : 'str',
        'defvalue' : [],
        'short_help' : "Pin Type",
        'param_help' : "cellname 'pin' name 'type' <str>",
        'help' : """
        Specifies pin type (data, clock, reset, set, tristate, 
        power, ground)
        """
    }

    pin['default']['cap'] = {
        'type' : 'num',
        'defvalue' : [],
        'short_help' : "Pin Type",
        'param_help' : "cellname 'pin' name 'cap' <num>",
        'help' : """
        Pin Capacitance
        """
    }
    
    pin['default']['timing']['default'] = {
        'type' : 'num',
        'defvalue' : [],
        'short_help' : "Pin Timing",
        'param_help' : "cellname 'pin' name 'cap' <num>",
        'example': ["lib.set('nand2_1x','pin','a','cap','0.5'"],
        'help' : """
        Pin Capacitance
        """
    }

    ########################
    # CIRCUIT
    ########################

    circuit['default']['w'] = {
        'type' : 'str',
        'defvalue' : [],
        'short_help' : "Transistor Width",
        'param_help' : "cellname 'circuit' instname 'w' <str>",
        'help' : """
        Transistor widths specified in nanometers.
        """
    }

    circuit['default']['l'] = {
        'type' : 'str',
        'defvalue' : [],
        'short_help' : "Transistor Length",
        'param_help' : "cellname 'circuit' instname 'l' <str>",
        'help' : """
        Transistor lengths specified in nanometers.
        """
    }
    
    circuit['default']['m'] = {
        'type' : 'str',
        'defvalue' : [],
        'short_help' : "Transistor Multiplier Value",
        'param_help' : "cellname 'circuit' instname 'm' <str>",
        'help' : """
        Transistor multiplier value. If m=5 and w=10, the total 
        width of the transistor is 50.
        """
    }

    circuit['default']['nf'] = {
        'type' : 'str',
        'defvalue' : [],
        'short_help' : "Transistor Device Finger Number",
        'param_help' : "cellname 'circuit' instname 'nf' <str>",
        'help' : """
        Transistor device finger number. Each finger has a gate width 
        of w/nf.
        """
    }

    circuit['default']['device'] = {
        'type' : 'str',
        'defvalue' : [],
        'short_help' : "Transistor Device Name",
        'param_help' : "cellname 'circuit' instname 'device' <str>",
        'help' : """
        Transistor device name.
        """
    }

    circuit['default']['ad'] = {
        'type' : 'num',
        'defvalue' : [],
        'short_help' : "Transistor Drain Area",
        'param_help' : "cellname 'circuit' instname 'ad' <num>",
        'help' : """
        Transistor drain area specified in nm^2.
        """
    }

    circuit['default']['as'] = {
        'type' : 'num',
        'defvalue' : [],
        'short_help' : "Transistor Source Area",
        'param_help' : "cellname 'circuit' instname 'as' <num>",
        'help' : """
        Transistor source area specified in nm^2.
        """
    }

    circuit['default']['pd'] = {
        'type' : 'num',
        'defvalue' : [],
        'short_help' : "Transistor Drain Perimeter",
        'param_help' : "cellname 'circuit' instname 'pd' <num>",
        'help' : """
        Transistor drain perimeter specified in nm.
        """
    }

    circuit['default']['ps'] = {
        'type' : 'num',
        'defvalue' : [],
        'short_help' : "Transistor Source Perimeter",
        'param_help' : "cellname 'circuit' instname 'ps' <num>",
        'help' : """
        Transistor source perimeter specified in nm.
        """
    }
    
    



