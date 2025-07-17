import pytest

from siliconcompiler import LibrarySchema, StdCellLibrarySchema
from siliconcompiler.schema import PerNode, Scope


def test_allkeys():
    lib = LibrarySchema("test")
    assert lib.allkeys("tool") == set()


def test_define_tool_parameter():
    lib = LibrarySchema("test")
    lib.define_tool_parameter(
        "yosys",
        "timingcorner",
        "str",
        "timing corner to use for synthesis"
    )

    assert lib.allkeys("tool") == set([('yosys', 'timingcorner')])
    param = lib.get("tool", "yosys", "timingcorner", field=None)
    assert param.get(field="type") == "str"
    assert param.get(field="pernode") == PerNode.NEVER
    assert param.get(field="scope") == Scope.GLOBAL
    assert param.get(field="help") == "timing corner to use for synthesis"
    assert param.get(field="shorthelp") == "timing corner to use for synthesis"
    assert param.default.get() is None


def test_define_tool_parameter_override_illegal():
    lib = LibrarySchema("test")
    lib.define_tool_parameter(
        "yosys",
        "timingcorner",
        "str",
        "timing corner to use for synthesis",
        pernode=PerNode.REQUIRED,
        scope=Scope.SCRATCH
    )

    assert lib.allkeys("tool") == set([('yosys', 'timingcorner')])
    param = lib.get("tool", "yosys", "timingcorner", field=None)
    assert param.get(field="type") == "str"
    assert param.get(field="pernode") == PerNode.NEVER
    assert param.get(field="scope") == Scope.GLOBAL
    assert param.get(field="help") == "timing corner to use for synthesis"
    assert param.get(field="shorthelp") == "timing corner to use for synthesis"
    assert param.default.get() is None


def test_define_tool_parameter_invalid_help():
    with pytest.raises(TypeError, match="help must be a string"):
        LibrarySchema("test").define_tool_parameter(
            "yosys",
            "timingcorner",
            "str",
            1.5
        )


def test_define_tool_parameter_multiline_help_empty_first_line():
    lib = LibrarySchema("test")
    lib.define_tool_parameter(
        "yosys",
        "timingcorner",
        "str",
        """
        timing corner to use for synthesis
        this is a multiline help
        """
    )

    assert lib.allkeys("tool") == set([('yosys', 'timingcorner')])
    param = lib.get("tool", "yosys", "timingcorner", field=None)
    assert param.get(field="type") == "str"
    assert param.get(field="help") == "timing corner to use for synthesis\nthis is a multiline help"
    assert param.get(field="shorthelp") == "timing corner to use for synthesis"


def test_define_tool_parameter_multiline_help():
    lib = LibrarySchema("test")
    lib.define_tool_parameter(
        "yosys",
        "timingcorner",
        "str",
        """timing corner to use for synthesis
        this is a multiline help
        """
    )

    assert lib.allkeys("tool") == set([('yosys', 'timingcorner')])
    param = lib.get("tool", "yosys", "timingcorner", field=None)
    assert param.get(field="type") == "str"
    assert param.get(field="help") == "timing corner to use for synthesis\nthis is a multiline help"
    assert param.get(field="shorthelp") == "timing corner to use for synthesis"


def test_define_tool_parameter_with_defvalue():
    lib = LibrarySchema("test")
    lib.define_tool_parameter(
        "yosys",
        "timingcorner",
        "str",
        "timing corner to use for synthesis",
        defvalue="slow"
    )

    assert lib.allkeys("tool") == set([('yosys', 'timingcorner')])
    param = lib.get("tool", "yosys", "timingcorner", field=None)
    assert param.get(field="type") == "str"
    assert param.get(field="help") == "timing corner to use for synthesis"
    assert param.get(field="shorthelp") == "timing corner to use for synthesis"
    assert param.default.get() == "slow"


def test_define_tool_parameter_with_defvalue_file():
    lib = LibrarySchema("test")
    lib.define_tool_parameter(
        "yosys",
        "liberty",
        "file",
        "liberty file for synthesis",
        defvalue="./this.lib",
        package="sc"
    )

    assert lib.allkeys("tool") == set([('yosys', 'liberty')])
    param = lib.get("tool", "yosys", "liberty", field=None)
    assert param.get(field="type") == "file"
    assert param.get(field="help") == "liberty file for synthesis"
    assert param.get(field="shorthelp") == "liberty file for synthesis"
    assert param.default.get() == "./this.lib"
    assert param.default.get(field="package") == "sc"
    assert param.get(field="copy") is False


def test_define_tool_parameter_with_defvalue_file_copy_on():
    lib = LibrarySchema("test")
    lib.define_tool_parameter(
        "yosys",
        "liberty",
        "file",
        "liberty file for synthesis",
        defvalue="./this.lib",
        copy=True
    )

    assert lib.allkeys("tool") == set([('yosys', 'liberty')])
    param = lib.get("tool", "yosys", "liberty", field=None)
    assert param.get(field="type") == "file"
    assert param.get(field="help") == "liberty file for synthesis"
    assert param.get(field="shorthelp") == "liberty file for synthesis"
    assert param.default.get() == "./this.lib"
    assert param.get(field="copy") is True


def test_stdlib_asic_keys():
    assert StdCellLibrarySchema().allkeys("asic") == {
        ('cells', 'antenna',),
        ('cells', 'clkbuf',),
        ('cells', 'clkgate',),
        ('cells', 'clklogic',),
        ('cells', 'decap',),
        ('cells', 'dontuse',),
        ('cells', 'endcap',),
        ('cells', 'filler',),
        ('cells', 'hold',),
        ('cells', 'tap',),
        ('cells', 'tie',),
        ('cornerfilesets', 'default',),
        ('site',)
    }


def test_add_asic_corner_fileset():
    lib = StdCellLibrarySchema("lib")
    with lib.active_fileset("models"):
        lib.add_file("test.lib")
        assert lib.add_asic_corner_fileset("slow")
    assert lib.get("asic", "cornerfilesets", "slow") == ["models"]


def test_add_asic_corner_fileset_multiple():
    lib = StdCellLibrarySchema("lib")
    with lib.active_fileset("models1"):
        lib.add_file("test.lib")
        assert lib.add_asic_corner_fileset("slow")
    with lib.active_fileset("models2"):
        lib.add_file("test.lib")
        assert lib.add_asic_corner_fileset("slow")
    assert lib.get("asic", "cornerfilesets", "slow") == ["models1", "models2"]


def test_add_asic_corner_fileset_without_active():
    lib = StdCellLibrarySchema("lib")
    with lib.active_fileset("models"):
        lib.add_file("test.lib")
    assert lib.add_asic_corner_fileset("slow", "models")


def test_add_asic_corner_fileset_missing_fileset():
    with pytest.raises(ValueError, match="models is not defined"):
        StdCellLibrarySchema("lib").add_asic_corner_fileset("slow", "models")


def test_add_asic_corner_fileset_invalid_fileset():
    with pytest.raises(TypeError, match="fileset must be a string"):
        StdCellLibrarySchema("lib").add_asic_corner_fileset("slow", 8)


def test_add_asic_cell_list():
    lib = StdCellLibrarySchema("lib")
    lib.add_asic_cell_list("dontuse", "*X0*")
    lib.add_asic_cell_list("dontuse", "*X1*")
    assert lib.get("asic", "cells", "dontuse") == ["*X0*", "*X1*"]


def test_add_asic_site():
    lib = StdCellLibrarySchema("lib")
    lib.add_asic_site("sc7p5site")
    assert lib.get("asic", "site") == ["sc7p5site"]
