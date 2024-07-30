from siliconcompiler import Chip, Library, Schema
from siliconcompiler.tools._common import input_provides, input_file_node_name, get_libraries

from tests.core.tools.fake import foo


def test_input_provides():
    chip = Chip('test')

    flow = 'test'
    chip.node(flow, 'onestep', foo)
    chip.node(flow, 'twostep', foo)
    chip.node(flow, 'finalstep', foo)
    chip.edge(flow, 'onestep', 'finalstep')
    chip.edge(flow, 'twostep', 'finalstep')

    chip.set('tool', 'fake', 'task', 'foo', 'output', 'test.txt', step='onestep', index='0')
    chip.set('tool', 'fake', 'task', 'foo', 'output', 'test.txt', step='twostep', index='0')
    chip.set('tool', 'fake', 'task', 'foo', 'input', 'test.txt', step='finalstep', index='0')

    in_prov = input_provides(chip, 'finalstep', '0', flow='test')
    assert 'test.txt' in in_prov

    assert len(in_prov['test.txt']) == 2
    assert ('onestep', '0') in in_prov['test.txt']
    assert ('twostep', '0') in in_prov['test.txt']


def test_input_provides_autoflow():
    chip = Chip('test')

    flow = 'test'
    chip.node(flow, 'onestep', foo)
    chip.node(flow, 'twostep', foo)
    chip.node(flow, 'finalstep', foo)
    chip.edge(flow, 'onestep', 'finalstep')
    chip.edge(flow, 'twostep', 'finalstep')

    chip.set('tool', 'fake', 'task', 'foo', 'output', 'test.txt', step='onestep', index='0')
    chip.set('tool', 'fake', 'task', 'foo', 'output', 'test.txt', step='twostep', index='0')
    chip.set('tool', 'fake', 'task', 'foo', 'input', 'test.txt', step='finalstep', index='0')

    chip.set('option', 'flow', 'test')

    in_prov = input_provides(chip, 'finalstep', '0')
    assert 'test.txt' in in_prov

    assert len(in_prov['test.txt']) == 2
    assert ('onestep', '0') in in_prov['test.txt']
    assert ('twostep', '0') in in_prov['test.txt']


def test_input_file_node_name():
    assert 'test.test0.txt' == input_file_node_name('test.txt', 'test', '0')
    assert 'test.test0.txt.gz' == input_file_node_name('test.txt.gz', 'test', '0')
    assert 'test.test0.txt.gz' == input_file_node_name('test.txt.GZ', 'test', '0')

    assert 'test.other0.txt' == input_file_node_name('test.txt', 'other', '0')
    assert 'test.other1.txt.gz' == input_file_node_name('test.txt.gz', 'other', '1')


def test_get_libraries():
    chip = Chip('<test>')

    lib = Library(chip, 'test')
    chip.set('option', 'library', 'test')
    chip.use(lib)

    chip.set('arg', 'step', Schema.GLOBAL_KEY)
    chip.set('arg', 'index', Schema.GLOBAL_KEY)

    assert get_libraries(chip) == set(['test'])


def test_get_libraries_recuriveloop():
    chip = Chip('<test>')

    lib = Library(chip, 'main_lib')
    lib.set('option', 'library', 'main_lib')

    chip.use(lib)
    chip.set('option', 'library', 'main_lib')

    chip.set('arg', 'step', Schema.GLOBAL_KEY)
    chip.set('arg', 'index', Schema.GLOBAL_KEY)

    assert get_libraries(chip) == set(['main_lib'])


def test_get_libraries_recurive():
    chip = Chip('<test>')

    lib = Library(chip, 'main_lib')
    tlib = Library(chip, 'test')
    lib.set('option', 'library', 'test')
    lib.use(tlib)

    chip.use(lib)
    chip.set('option', 'library', 'main_lib')

    chip.set('arg', 'step', Schema.GLOBAL_KEY)
    chip.set('arg', 'index', Schema.GLOBAL_KEY)

    assert get_libraries(chip) == set(['main_lib', 'test'])


def test_recursive_import_with_option_library():
    chip = Chip('<test>')

    lib = Library(chip, 'main_lib')
    sub_lib = Library(chip, 'sub_lib')
    lib.set('option', 'library', 'sub_lib')
    lib.use(sub_lib)

    chip.use(lib)
    chip.set('option', 'library', 'main_lib')

    chip.set('arg', 'step', Schema.GLOBAL_KEY)
    chip.set('arg', 'index', Schema.GLOBAL_KEY)

    assert get_libraries(chip) == set(['main_lib', 'sub_lib'])
