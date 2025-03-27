import pytest
from siliconcompiler import Chip, Library, Flow, PDK, Checklist, FPGA
from siliconcompiler.use import PackageChip


def test_module_input():
    chip = Chip('test')

    lib = Library('testlib')
    chip.use(lib)

    assert 'testlib' in chip.getkeys('library')


def test_function_input():
    chip = Chip('test')

    def func(chip):
        return Library('testlib')
    chip.use(func)

    assert 'testlib' in chip.getkeys('library')


def test_none_input():
    chip = Chip('test')

    with pytest.raises(ValueError):
        chip.use(None)


def test_function_spec():
    chip = Chip('test')

    def func(chip, other):
        pass

    with pytest.raises(RuntimeError):
        chip.use(func)


def test_chip_passing():
    chip = Chip('test')

    def func(chip):
        assert isinstance(chip, Chip)

    chip.use(func)


def test_chip_not_passing():
    chip = Chip('test')

    def func():
        raise EnvironmentError

    with pytest.raises(EnvironmentError):
        chip.use(func)


def test_target_return(caplogger):
    chip = Chip('test')
    log = caplogger(chip)

    def func(chip):
        return [Library('test')]

    chip.use(func)

    assert "Target returned items, which it should not have" in log()


def test_library_return(caplogger):
    chip = Chip('test')
    log = caplogger(chip)

    def func():
        return [Library('test')]

    chip.use(func)

    assert "Target returned items, which it should not have" not in log()


def test_load_target_string():
    chip = Chip('test')

    with pytest.raises(ValueError):
        chip.load_target('testing')


def test_packagechip_multiple_packages():
    with pytest.raises(ValueError,
                       match="{'test1': {'path': 'test'}, 'test2': {'path': 'test'}} "
                             "cannot contain multiple packages."):
        PackageChip("test", package={
            "test1": {"path": "test"},
            "test2": {"path": "test"}
        })


def test_packagechip_input():
    lib = Library("test", package={"test1": {"path": "test"}})
    lib.input("testfile.v")
    assert lib.get("input", "rtl", "verilog", field="package") == ["test1"]


def test_packagechip_output():
    lib = Library("test", package={"test1": {"path": "test"}})
    lib.output("testfile.v")
    assert lib.get("output", "rtl", "verilog", field="package") == ["test1"]


@pytest.mark.parametrize("cls", (Library, Flow, PDK, Checklist, FPGA))
def test_deprecated_passing_chip(cls, caplogger):
    chip = Chip("")

    log = caplogger(chip)

    cls_name = cls.__name__.split(".")[-1]

    cls(chip, "name")

    assert f"passing Chip object to name ({cls_name}) is deprecated" in log()
