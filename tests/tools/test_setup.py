import sys
import pytest
import os
import siliconcompiler
import importlib

if __name__ != "__main__":
    from tests.fixtures import test_wrapper

def test_verilator():
    '''Verilator tool test
    '''
    # setup tool
    chip = siliconcompiler.Chip()
    setup_tool(chip, 'verilator','import')

def test_openroad():
    '''Openroad tool test
    '''
    # setup tool
    chip = siliconcompiler.Chip()
    setup_tool(chip, 'openroad','route')

def test_yosys():
    '''Yosys tool test
    '''
    # setup tool
    chip = siliconcompiler.Chip()
    setup_tool(chip, 'yosys','syn')

def test_klayout():
    '''Klayout tool test
    '''
    # setup tool
    chip = siliconcompiler.Chip()
    setup_tool(chip, 'klayout','export')

def test_ghdl():
    '''GHDL tool test
    '''
    # setup tool
    chip = siliconcompiler.Chip()
    setup_tool(chip, 'ghdl','import')

def test_morty():
    '''Morty tool test
    '''
    # setup tool
    chip = siliconcompiler.Chip()
    setup_tool(chip, 'morty','import')

def test_surelog():
    '''Surelog tool test
    '''
    # setup tool
    chip = siliconcompiler.Chip()
    setup_tool(chip, 'surelog','import')

def test_openfpga():
    '''Openfpga tool test
    '''
    # setup tool
    chip = siliconcompiler.Chip()
    setup_tool(chip, 'openfpga','apr')

def test_xyce():
    '''Xyce tool test
    '''
    # setup tool
    chip = siliconcompiler.Chip()
    setup_tool(chip, 'xyce','spice')

def test_icepack():
    '''Icepack tool test
    '''
    # setup tool
    chip = siliconcompiler.Chip()
    setup_tool(chip, 'icepack','bitstream')

def test_vpr():
    '''VPR tool test
    '''
    # setup tool
    chip = siliconcompiler.Chip()
    setup_tool(chip, 'vpr','apr')

def test_vivado():
    '''Vivado tool test
    '''
    # setup tool
    chip = siliconcompiler.Chip()
    setup_tool(chip, 'vivado','compile')

def test_nextpnr():
    '''Vivado tool test
    '''
    # setup tool
    chip = siliconcompiler.Chip()
    setup_tool(chip, 'nextpnr','apr')

def test_sv2v():
    '''SV2V tool test
    '''
    # setup tool
    chip = siliconcompiler.Chip()
    setup_tool(chip, 'sv2v','import')


def setup_tool(chip,tool,step):

    # standard setup
    chip.target("freepdk45")
    chip.set('design', '<design>')

    # load module
    searchdir = "siliconcompiler.tools." + tool
    modulename = '.'+tool+'_setup'
    module = importlib.import_module(modulename, package=searchdir)
    setup_tool = getattr(module, "setup_tool")
    setup_tool(chip, step, '0')
    # check result
    localcfg = chip.getcfg('eda',tool)
    chip.writecfg(tool + '_setup.json', cfg=localcfg)
    assert os.path.isfile(tool+'_setup.json')
