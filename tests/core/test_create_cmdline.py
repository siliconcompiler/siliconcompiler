import siliconcompiler

def test_cli_multi_source(monkeypatch):
    ''' Regression test for bug where CLI parser wasn't handling multiple
    source files properly.
    '''
    chip = siliconcompiler.Chip('test')

    # I think it doesn't matter if these files actually exist, since we're just
    # checking that the CLI app parses them correctly
    args = ['sc',
            "-source 'verilog examples/ibex/ibex_alu.v'",
            "-source 'verilog examples/ibex/ibex_branch_predict.v'",
            '-target', 'freepdk45_demo']

    monkeypatch.setattr('sys.argv', args)
    chip.create_cmdline('sc')

    assert chip.get('source','verilog') == ['examples/ibex/ibex_alu.v',
                                            'examples/ibex/ibex_branch_predict.v']
    assert chip.get('option','target') == 'freepdk45_demo'

def test_cli_include_flag(monkeypatch):
    ''' Regression test for bug where CLI parser wasn't handling multiple
    source files properly.
    '''
    chip = siliconcompiler.Chip('test')

    # It doesn't matter that these files/dirs don't exist, since we're just
    # checking that the CLI app parses them correctly
    args = ['sc',
            "-source 'verilog source.v'",
            '-I', 'include/inc1', '+incdir+include/inc2']

    monkeypatch.setattr('sys.argv', args)
    chip.create_cmdline('sc')

    assert chip.get('source', 'verilog') == ['source.v']
    assert chip.get('option', 'idir') == ['include/inc1', 'include/inc2']
