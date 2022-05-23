import siliconcompiler

def do_cli_test(args, monkeypatch):
    chip = siliconcompiler.Chip('test')
    monkeypatch.setattr('sys.argv', args)
    chip.create_cmdline('sc')
    return chip

def test_cli_multi_source(monkeypatch):
    ''' Regression test for bug where CLI parser wasn't handling multiple
    source files properly.
    '''
    # I think it doesn't matter if these files actually exist, since we're just
    # checking that the CLI app parses them correctly
    args = ['sc',
            '-input', 'verilog examples/ibex/ibex_alu.v',
            '-input', 'verilog examples/ibex/ibex_branch_predict.v',
            '-target', 'freepdk45_demo']

    chip = do_cli_test(args, monkeypatch)

    assert chip.get('input','verilog') == ['examples/ibex/ibex_alu.v',
                                           'examples/ibex/ibex_branch_predict.v']
    assert chip.get('option','target') == 'freepdk45_demo'

def test_cli_include_flag(monkeypatch):
    ''' Regression test for bug where CLI parser wasn't handling multiple
    source files properly.
    '''
    args = ['sc',
            '-input', 'verilog source.v',
            '-I', 'include/inc1', '+incdir+include/inc2']

    chip = do_cli_test(args, monkeypatch)

    assert chip.get('input', 'verilog') == ['source.v']
    assert chip.get('option', 'idir') == ['include/inc1', 'include/inc2']

def test_optmode(monkeypatch):
    '''Test optmode special handling.'''
    args = ['sc', '-O3']

    chip = do_cli_test(args, monkeypatch)

    assert chip.get('option', 'optmode') == 'O3'
