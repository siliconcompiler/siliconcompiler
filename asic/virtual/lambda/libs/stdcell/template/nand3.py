

def cell_nand3(lib):

    name = 'NAND3'
    
    #Global definitions
    lib[name]['width'] = 0
    lib[name]['height'] = 0
    
    #Output
    lib[name]['pin']['Y'] = {
        'direction' : 'output',
        'function' : "~(A & B & C)"
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

    lib[name]['pin']['C'] = {
        'direction' : 'input',
        'type' : 'data'
    }
    
    return lib
    
    

