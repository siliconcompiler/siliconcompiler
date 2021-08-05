

def cell_dff(lib):

    name = 'DFF'
    
    #Width/Height
    lib[name]['width'] = 0
    lib[name]['height'] = 0
    
    #Output
    lib[name]['pin']['Q'] = {
        'direction' : 'output',
        'type'     : 'ff',
        'function' : 'D',
        'clock'    : 'CLK'
    }

    #Inputs
    lib[name]['pin']['CLK'] = {
        'direction' : 'input',
        'type' : 'clock'
    }
    lib[name]['pin']['D'] = {
        'direction' : 'input',
        'type' : 'data'
    }
    
    return lib
    
    

