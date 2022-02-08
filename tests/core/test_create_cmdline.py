import siliconcompiler

def test_cli_multi_source(monkeypatch):
    ''' Regression test for bug where CLI parser wasn't handling multiple
    source files properly.
    '''
    chip = siliconcompiler.Chip()

    # I think it doesn't matter if these files actually exist, since we're just
    # checking that the CLI app parses them correctly
    args = ['sc', 'examples/ibex/ibex_alu.v', 'examples/ibex/ibex_branch_predict.v',
            '-target_project', 'freepdk45_demo']

    monkeypatch.setattr('sys.argv', args)
    chip.create_cmdline('sc')

    assert chip.get('source') == ['examples/ibex/ibex_alu.v',
                                  'examples/ibex/ibex_branch_predict.v']
    assert chip.get('target', 'project') == 'freepdk45_demo'

def test_cli_include_flag(monkeypatch):
    ''' Regression test for bug where CLI parser wasn't handling multiple
    source files properly.
    '''
    chip = siliconcompiler.Chip()

    # It doesn't matter that these files/dirs don't exist, since we're just
    # checking that the CLI app parses them correctly
    args = ['sc', 'source.v', '-I', 'include/inc1', '+incdir+include/inc2']

    monkeypatch.setattr('sys.argv', args)
    chip.create_cmdline('sc')

    assert chip.get('source') == ['source.v']
    assert chip.get('idir') == ['include/inc1', 'include/inc2']
