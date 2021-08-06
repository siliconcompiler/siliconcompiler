

def cell_xor2(lib):

    name = 'XOR2'
    
    #Global definitions
    lib[name]['width'] = 0
    lib[name]['height'] = 0
    
    #Output
    lib[name]['pin']['Y'] = {
        'direction' : 'output',
        'type' : 'comb',
        'function' : "(A ^ B)"
    }

    #Inputs
    lib[name]['pin']['A'] = {
        'direction' : 'input',
        'type' : 'data'
    }
    lib[name]['pin']['B'] = {
        'direction' : 'input',
        'type' : 'data'
    }
    
    return lib
    
    

