import os

from siliconcompiler import Chip, Library, Schema
from siliconcompiler.tools._common import input_provides, input_file_node_name, get_libraries, \
    add_require_input
from siliconcompiler.tools._common.asic import get_libraries as get_asic_libraries, CellArea
from siliconcompiler.tools._common.asic_clock import get_clock_period

from core.tools.fake import foo
import pytest


def test_add_input_require_verilog():
    chip = Chip('test')

    flow = 'test'
    chip.node(flow, 'onestep', foo)

    chip.input('test.v')

    chip.set('option', 'flow', flow)
    chip.set('arg', 'step', 'onestep')
    chip.set('arg', 'index', '0')

    assert add_require_input(chip, 'input', 'rtl', 'verilog')
    assert not add_require_input(chip, 'input', 'rtl', 'systemverilog')

    assert chip.get('tool', 'fake', 'task', 'foo', 'require',
                    step='onestep', index='0') == \
        ['input,rtl,verilog']


def test_add_input_require_systemverilog():
    chip = Chip('test')

    flow = 'test'
    chip.node(flow, 'onestep', foo)

    chip.input('test.sv')

    chip.set('option', 'flow', flow)
    chip.set('arg', 'step', 'onestep')
    chip.set('arg', 'index', '0')

    assert not add_require_input(chip, 'input', 'rtl', 'verilog')
    assert add_require_input(chip, 'input', 'rtl', 'systemverilog')

    assert chip.get('tool', 'fake', 'task', 'foo', 'require',
                    step='onestep', index='0') == \
        ['input,rtl,systemverilog']


def test_add_input_require_mixedverilog():
    chip = Chip('test')

    flow = 'test'
    chip.node(flow, 'onestep', foo)

    chip.input('test.v')
    chip.input('test.sv')

    chip.set('option', 'flow', flow)
    chip.set('arg', 'step', 'onestep')
    chip.set('arg', 'index', '0')

    assert add_require_input(chip, 'input', 'rtl', 'verilog')
    assert add_require_input(chip, 'input', 'rtl', 'systemverilog')

    assert chip.get('tool', 'fake', 'task', 'foo', 'require',
                    step='onestep', index='0') == \
        ['input,rtl,verilog', 'input,rtl,systemverilog']


def test_add_input_require_mixedverilog_library():
    chip = Chip('<test>')

    flow = 'test'
    chip.node(flow, 'onestep', foo)
    chip.set('option', 'flow', flow)
    chip.set('arg', 'step', 'onestep')
    chip.set('arg', 'index', '0')

    lib = Library('test')
    lib.input("testing.v")
    lib.input("testing.sv")
    chip.use(lib)
    chip.set('option', 'library', 'test')

    chip.input("testing.sv")

    assert add_require_input(chip, 'input', 'rtl', 'verilog')
    assert add_require_input(chip, 'input', 'rtl', 'systemverilog')

    assert chip.get('tool', 'fake', 'task', 'foo', 'require',
                    step='onestep', index='0') == \
        ['library,test,input,rtl,verilog',
         'input,rtl,systemverilog',
         'library,test,input,rtl,systemverilog']


def test_add_input_require_mixedverilog_library_dont_follow():
    chip = Chip('<test>')

    flow = 'test'
    chip.node(flow, 'onestep', foo)
    chip.set('option', 'flow', flow)
    chip.set('arg', 'step', 'onestep')
    chip.set('arg', 'index', '0')

    lib = Library('test')
    lib.input("testing.v")
    lib.input("testing.sv")
    chip.use(lib)
    chip.set('option', 'library', 'test')

    chip.input("testing.sv")

    assert not add_require_input(chip, 'input', 'rtl', 'verilog', include_library_files=False)
    assert add_require_input(chip, 'input', 'rtl', 'systemverilog')

    assert chip.get('tool', 'fake', 'task', 'foo', 'require',
                    step='onestep', index='0') == \
        ['input,rtl,systemverilog',
         'library,test,input,rtl,systemverilog']


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


def test_input_provides_with_prune():
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

    chip.set('option', 'prune', ('twostep', '0'))

    in_prov = input_provides(chip, 'finalstep', '0', flow='test')
    assert 'test.txt' in in_prov

    assert len(in_prov['test.txt']) == 1
    assert ('onestep', '0') in in_prov['test.txt']
    assert ('twostep', '0') not in in_prov['test.txt']


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

    lib = Library('test')
    chip.set('option', 'library', 'test')
    chip.use(lib)

    chip.set('arg', 'step', Schema.GLOBAL_KEY)
    chip.set('arg', 'index', Schema.GLOBAL_KEY)

    assert get_libraries(chip) == set(['test'])


def test_get_libraries_recuriveloop():
    chip = Chip('<test>')

    lib = Library('main_lib')
    lib.set('option', 'library', 'main_lib')

    chip.use(lib)
    chip.set('option', 'library', 'main_lib')

    chip.set('arg', 'step', Schema.GLOBAL_KEY)
    chip.set('arg', 'index', Schema.GLOBAL_KEY)

    assert get_libraries(chip) == set(['main_lib'])


def test_get_libraries_recurive():
    chip = Chip('<test>')

    lib = Library('main_lib')
    tlib = Library('test')
    lib.set('option', 'library', 'test')
    lib.use(tlib)

    chip.use(lib)
    chip.set('option', 'library', 'main_lib')

    chip.set('arg', 'step', Schema.GLOBAL_KEY)
    chip.set('arg', 'index', Schema.GLOBAL_KEY)

    assert get_libraries(chip) == set(['main_lib', 'test'])


def test_recursive_import_with_option_library():
    chip = Chip('<test>')

    lib = Library('main_lib')
    sub_lib = Library('sub_lib')
    lib.set('option', 'library', 'sub_lib')
    lib.use(sub_lib)

    chip.use(lib)
    chip.set('option', 'library', 'main_lib')

    chip.set('arg', 'step', Schema.GLOBAL_KEY)
    chip.set('arg', 'index', Schema.GLOBAL_KEY)

    assert get_libraries(chip) == set(['main_lib', 'sub_lib'])


@pytest.mark.parametrize("libtype", ("logic", "macro"))
def test_get_libraries_asic_none(libtype):
    chip = Chip('<test>')

    lib = Library('test')
    chip.set('option', 'library', 'test')
    chip.use(lib)

    chip.set('arg', 'step', Schema.GLOBAL_KEY)
    chip.set('arg', 'index', Schema.GLOBAL_KEY)

    assert get_asic_libraries(chip, libtype) == []


def test_get_libraries_asic_invalid():
    chip = Chip('<test>')

    lib = Library('test')
    chip.set('option', 'library', 'test')
    chip.use(lib)

    chip.set('arg', 'step', Schema.GLOBAL_KEY)
    chip.set('arg', 'index', Schema.GLOBAL_KEY)

    with pytest.raises(ValueError):
        get_asic_libraries(chip, 'error')


@pytest.mark.parametrize("libtype", ("logic", "macro"))
def test_get_libraries_asic_single(libtype):
    chip = Chip('<test>')

    lib = Library('test')
    chip.set('option', 'library', 'test')
    chip.use(lib)
    chip.add('asic', f'{libtype}lib', 'testlib')

    chip.set('arg', 'step', Schema.GLOBAL_KEY)
    chip.set('arg', 'index', Schema.GLOBAL_KEY)

    assert get_asic_libraries(chip, libtype) == ['testlib']


@pytest.mark.parametrize("libtype", ("logic", "macro"))
def test_get_libraries_asic_sub_import_single(libtype):
    chip = Chip('<test>')

    lib = Library('test')
    lib.add('asic', f'{libtype}lib', 'testlib')
    chip.set('option', 'library', 'test')
    chip.use(lib)

    chip.set('arg', 'step', Schema.GLOBAL_KEY)
    chip.set('arg', 'index', Schema.GLOBAL_KEY)

    assert get_asic_libraries(chip, libtype) == ['testlib']


@pytest.mark.parametrize("libtype", ("logic", "macro"))
def test_get_libraries_asic_sub_import_overlapping(libtype):
    chip = Chip('<test>')

    lib = Library('test')
    lib.add('asic', f'{libtype}lib', 'testlib')
    chip.set('option', 'library', 'test')
    chip.use(lib)
    chip.add('asic', f'{libtype}lib', 'testlib')

    chip.set('arg', 'step', Schema.GLOBAL_KEY)
    chip.set('arg', 'index', Schema.GLOBAL_KEY)

    assert get_asic_libraries(chip, libtype) == ['testlib']


@pytest.mark.parametrize("libtype", ("logic", "macro"))
def test_get_libraries_asic_sub_import_differnet(libtype):
    chip = Chip('<test>')

    lib = Library('test')
    lib.add('asic', f'{libtype}lib', 'testlib')
    chip.set('option', 'library', 'test')
    chip.use(lib)
    chip.add('asic', f'{libtype}lib', 'testlib2')

    chip.set('arg', 'step', Schema.GLOBAL_KEY)
    chip.set('arg', 'index', Schema.GLOBAL_KEY)

    assert get_asic_libraries(chip, libtype) == ['testlib2', 'testlib']


@pytest.mark.parametrize("libtype", ("logic", "macro"))
def test_get_libraries_asic_sub_not_enabled(libtype):
    chip = Chip('<test>')

    lib = Library('test')
    lib.add('asic', f'{libtype}lib', 'testlib')
    chip.use(lib)
    chip.add('asic', f'{libtype}lib', 'testlib2')

    chip.set('arg', 'step', Schema.GLOBAL_KEY)
    chip.set('arg', 'index', Schema.GLOBAL_KEY)

    assert get_asic_libraries(chip, libtype) == ['testlib2']


def test_cell_area():
    report = CellArea()

    assert report.size() == 0

    report.addCell()
    assert report.size() == 0

    report.addCell(name="test1", module="mod")
    assert report.size() == 0

    report.addCell(name="test1", module="mod", cellcount=1, cellarea=2)
    assert report.size() == 1

    report.addCell(module="mod", cellcount=1, cellarea=2)
    assert report.size() == 2

    report.addCell(module="mod", cellcount=1, cellarea=2)
    assert report.size() == 3

    report.writeReport("test.json")

    assert os.path.isfile("test.json")


@pytest.mark.parametrize(
        "sdc_file,scale,period",
        [
            ("sdc_with_variable.sdc", 1, 10),
            ("sdc_with_nested.sdc", 1, 10),
            ("sdc_with_number0.sdc", 1, 10),
            ("sdc_with_number1.sdc", 1, 10.5),
            ("sdc_with_variable.sdc", 1e-12, 10e-12),
            ("sdc_with_number0.sdc", 1e-12, 10e-12),
            ("sdc_with_number1.sdc", 1e-12, 10.5e-12),
            ("sdc_with_nested.sdc", 1e-9, 10e-9),
        ])
def test_get_clock_period_sdc(datadir, sdc_file, scale, period):
    chip = Chip('')
    chip.input(f"{datadir}/{sdc_file}")
    chip.set('arg', 'step', 'test')
    chip.set('arg', 'index', '0')
    chip.clock('clock', 9)
    name, sdc_period = get_clock_period(chip, scale)

    assert name is None
    assert sdc_period == period


def test_get_clock_period_none():
    chip = Chip('')
    chip.set('arg', 'step', 'test')
    chip.set('arg', 'index', '0')
    name, sdc_period = get_clock_period(chip, 1)

    assert name is None
    assert sdc_period is None


@pytest.mark.parametrize(
        "scale,period",
        [
            (1, 10),
            (1, 10.5)
        ])
def test_get_clock_period_key(scale, period):
    chip = Chip('')
    chip.set('arg', 'step', 'test')
    chip.set('arg', 'index', '0')
    chip.clock('clock', period)
    chip.clock('clock2', period * 2)
    name, sdc_period = get_clock_period(chip, scale)

    assert name == 'clock'
    assert f"{sdc_period:.3f}" == f"{period:.3f}"
