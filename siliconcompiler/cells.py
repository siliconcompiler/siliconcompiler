# Copyright 2021 Silicon Compiler Authors. All Rights Reserved.


###############################################################################
# HELPER FUNCTIONS
###############################################################################

def cell_pin(cell, pin, direction, func=None):

    if not 'pin' in cell:
        cell['pin'] = {}
        
    cell['pin'][pin] = {}
    cell['pin'][pin]['dir'] = direction
    if func is not None:
        cell['pin'][pin]['function'] = func

###############################################################################
# NANDS
###############################################################################

def cell_nand2(lib, name):

    lib[name] = {}
    
    # Properties
    lib[name]['property'] = {
        'leakage': 0,        
        'width' : 0,
        'height' : 0
    }

    # Cell function
    lib[name]['function'] = {
        'type': 'comb',
        'logic' : '~(A & B)',
        'output' : ['IY','IYN'],        
    }

    # Pins
    cell_pin(lib[name], 'A', 'input')
    cell_pin(lib[name], 'B', 'input')
    cell_pin(lib[name], 'Y', 'output', func='IY')
    
###############################################################################
# NORS
###############################################################################

###############################################################################
# FLIP-FLOPS
###############################################################################

def cell_dff(lib, name):

    lib[name] = {}

    # Width/Height
    lib[name]['property'] = {
        'leakage': 0,        
        'width' : 0,
        'height' : 0
    }

    # Cell function
    lib[name]['function'] = {
        'type': 'ff',
        'logic': 'D',
        'clocked_on': 'CK',
        'outputs' : ['IQ','IQN']      
    }

    # Pins Assignment
    cell_pin(lib[name], 'CK', 'input')
    cell_pin(lib[name], 'D', 'input')
    cell_pin(lib[name], 'Q', 'output', func='IQ')


def cell_sdffr(lib, name):

    lib[name] = {}

    # Width/Height
    lib[name]['property'] = {
        'leakage': 0,        
        'width' : 0,
        'height' : 0
    }

    # Cell Function
    lib[name]['function'] = {
        'type': 'ff',
        'logic': '((SE & SI) | (D & ~SE))', 
        'clocked_on': 'CK',
        'clear': '~RN',
        'outputs' : ['IQ','IQN']      
    }

    # Pins Assignment
    cell_pin(lib[name], 'CK', 'input')
    cell_pin(lib[name], 'D', 'input')
    cell_pin(lib[name], 'RN', 'input')
    cell_pin(lib[name], 'SE', 'input')
    cell_pin(lib[name], 'SI', 'input')
    cell_pin(lib[name], 'Q', 'output', func='IQ')
    
###############################################################################
# LATCHES
###############################################################################

###############################################################################
# RAM
###############################################################################


###############################################################################
# Testing Purposese
###############################################################################
if __name__ == '__main__':

    lib = {}
    
    cell_nand2(lib, 'NAND2')
    cell_dff(lib, 'DFF')
    cell_sdffr(lib, 'SDFFR')
