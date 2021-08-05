

def cell_nor2(lib):

    name = 'NOR2'
    
    #Global definitions
    lib[name]['width'] = 0
    lib[name]['height'] = 0
    
    #Output
    lib[name]['pin']['Y'] = {
        'type' : 'comb',
        'direction' : 'output',
        'function' : "~(A | B)"
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
    
    

