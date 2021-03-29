
def setup_eda (chip):
    '''Default EDA flow for ASIC implementation. To customize this flow, 
    create a new file called eda_"yourname".py and user in your triplet
    target.
    '''
    chip.cfg['flow_design']['value'] = ['import',
                                        'syn',
                                        'floorplan',
                                        'place',
                                        'cts',
                                        'route',
                                        'dfm',
                                        'export']

    for step in chip.cfg['flow_design']['value']:
        if step == 'import':
            vendor = 'verilator'
        elif step == 'export':
            vendor = 'klayout'
        else:
            vendor = 'export'
        edadir = "eda." + vendor
        module = importlib.import_module('.'+vendor, package=edadir)
        setup_tool = getattr(module,"setup_tool")
        setup_tool(chip, step)
