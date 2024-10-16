import os

from siliconcompiler import PDK


####################################################
# PDK Setup
####################################################
def setup():
    '''
    Faux PDK
    '''

    pdkdir = os.path.dirname(__file__)

    pdk = PDK('faux', package=('faux_pdk', pdkdir))

    # process name
    pdk.set('pdk', 'faux', 'foundry', 'virtual')
    pdk.set('pdk', 'faux', 'node', 130)
    pdk.set('pdk', 'faux', 'wafersize', 200)

    stackup = 'M5'

    pdk.set('pdk', 'faux', 'stackup', stackup)
    pdk.set('pdk', 'faux', 'drc', 'runset', 'klayout', stackup, 'drc', 'interposer.drc')

    pdk.add('pdk', 'faux', 'var', 'klayout', stackup, 'drc_params:drc', 'input=<input>')
    pdk.add('pdk', 'faux', 'var', 'klayout', stackup, 'drc_params:drc', 'topcell=<topcell>')
    pdk.add('pdk', 'faux', 'var', 'klayout', stackup, 'drc_params:drc', 'report=<report>')
    pdk.add('pdk', 'faux', 'var', 'klayout', stackup, 'drc_params:drc', 'threads=<threads>')

    pdk.set('pdk', 'faux', 'display', 'klayout', stackup, 'layers.lyp')

    return pdk
