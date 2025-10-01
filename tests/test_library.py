import pytest

from siliconcompiler import PDK
from siliconcompiler.library import LibrarySchema, ToolLibrarySchema, StdCellLibrary
from siliconcompiler.schema import PerNode, Scope
from siliconcompiler.schema_support.packageschema import PackageSchema


def test_allkeys():
    lib = LibrarySchema("test")
    assert lib.allkeys() == set([
        ('dataroot', 'default', 'path'),
        ('dataroot', 'default', 'tag'),
        ('fileset', 'default', 'file', 'default'),
        ('package', 'version'),
        ('package', 'doc', 'userguide'),
        ('package', 'doc', 'quickstart'),
        ('package', 'author', 'default', 'email'),
        ('package', 'licensefile'),
        ('package', 'license'),
        ('package', 'doc', 'reference'),
        ('package', 'doc', 'tutorial'),
        ('package', 'doc', 'signoff'),
        ('package', 'doc', 'datasheet'),
        ('package', 'doc', 'releasenotes'),
        ('package', 'author', 'default', 'organization'),
        ('package', 'doc', 'testplan'),
        ('package', 'description'),
        ('package', 'vendor'),
        ('package', 'author', 'default', 'name')
    ])


def test_getdict_type():
    assert LibrarySchema._getdict_type() == "LibrarySchema"


def test_toollib_getdict_type():
    assert ToolLibrarySchema._getdict_type() == "ToolLibrarySchema"


def test_package_access():
    lib = LibrarySchema()
    assert lib.get("package", field="schema") is lib.package
    assert isinstance(lib.package, PackageSchema)


def test_allkeys_tool_library():
    lib = ToolLibrarySchema("test")
    assert lib.allkeys() == set([
        ('dataroot', 'default', 'path'),
        ('dataroot', 'default', 'tag'),
        ('fileset', 'default', 'file', 'default'),
        ('package', 'version'),
        ('package', 'doc', 'userguide'),
        ('package', 'doc', 'quickstart'),
        ('package', 'author', 'default', 'email'),
        ('package', 'licensefile'),
        ('package', 'license'),
        ('package', 'doc', 'reference'),
        ('package', 'doc', 'tutorial'),
        ('package', 'doc', 'signoff'),
        ('package', 'doc', 'datasheet'),
        ('package', 'doc', 'releasenotes'),
        ('package', 'author', 'default', 'organization'),
        ('package', 'doc', 'testplan'),
        ('package', 'description'),
        ('package', 'vendor'),
        ('package', 'author', 'default', 'name')
    ])
    assert lib.allkeys("tool") == set()


def test_define_tool_parameter():
    lib = ToolLibrarySchema("test")
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


def test_define_tool_parameter_recovered():
    class TestTool(ToolLibrarySchema):
        def __init__(self, name=None):
            super().__init__()
            self.set_name(name)

            self.define_tool_parameter("openroad", "param1", "str", "help")

    lib = TestTool("test")
    lib.define_tool_parameter(
        "yosys",
        "oneparam",
        "str",
        "timing corner to use for synthesis"
    )
    lib.define_tool_parameter(
        "yosys",
        "twoparam",
        "[(str,float)]",
        "timing corner to use for synthesis"
    )
    lib.define_tool_parameter(
        "openroad",
        "param2",
        "[(str,float)]",
        "timing corner to use for synthesis"
    )

    lib.set("tool", "openroad", "param1", "openroad_param")
    lib.set("tool", "openroad", "param2", [("this0", -2), ("test1", -5)])
    lib.set("tool", "yosys", "oneparam", "yosys_setting")
    lib.set("tool", "yosys", "twoparam", [("this0", 12), ("test1", 14)])

    assert lib.allkeys("tool") == set([('yosys', 'oneparam'),
                                       ('yosys', 'twoparam'),
                                       ("openroad", "param1"),
                                       ("openroad", "param2")])

    new_lib = TestTool.from_manifest(name="newlib", cfg=lib.getdict())

    assert new_lib.allkeys("tool") == set([('yosys', 'oneparam'),
                                           ('yosys', 'twoparam'),
                                           ("openroad", "param1"),
                                           ("openroad", "param2")])

    assert new_lib.get("tool", "openroad", "param1") == "openroad_param"
    assert new_lib.get("tool", "openroad", "param2") == [("this0", -2), ("test1", -5)]
    assert new_lib.get("tool", "yosys", "oneparam") == "yosys_setting"
    assert new_lib.get("tool", "yosys", "twoparam") == [("this0", 12), ("test1", 14)]


def test_define_tool_parameter_override_illegal():
    lib = ToolLibrarySchema("test")
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
        ToolLibrarySchema("test").define_tool_parameter(
            "yosys",
            "timingcorner",
            "str",
            1.5
        )


def test_define_tool_parameter_empty_help():
    with pytest.raises(ValueError, match="help is required"):
        ToolLibrarySchema("test").define_tool_parameter(
            "yosys",
            "timingcorner",
            "str",
            ""
        )


def test_define_tool_parameter_multiline_help_empty_first_line():
    lib = ToolLibrarySchema("test")
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
    lib = ToolLibrarySchema("test")
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
    lib = ToolLibrarySchema("test")
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
    lib = ToolLibrarySchema("test")
    lib.define_tool_parameter(
        "yosys",
        "liberty",
        "file",
        "liberty file for synthesis",
        defvalue="./this.lib",
        dataroot="sc"
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
    lib = ToolLibrarySchema("test")
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
    assert StdCellLibrary().allkeys("asic") == {
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
        ('libcornerfileset', 'default', 'default'),
        ('pexcornerfileset', 'default'),
        ('aprfileset',),
        ('site',),
        ('pdk',),
        ('stackup',)
    }


def test_add_asic_libcornerfileset():
    lib = StdCellLibrary("lib")
    with lib.active_fileset("models"):
        lib.add_file("test.lib")
        assert lib.add_asic_libcornerfileset("slow", "nldm")
    assert lib.get("asic", "libcornerfileset", "slow", "nldm") == ["models"]


def test_add_asic_libcornerfileset_multiple():
    lib = StdCellLibrary("lib")
    with lib.active_fileset("models1"):
        lib.add_file("test.lib")
        assert lib.add_asic_libcornerfileset("slow", "nldm")
    with lib.active_fileset("models2"):
        lib.add_file("test.lib")
        assert lib.add_asic_libcornerfileset("slow", "nldm")
    assert lib.get("asic", "libcornerfileset", "slow", "nldm") == ["models1", "models2"]


def test_add_asic_libcornerfileset_without_active():
    lib = StdCellLibrary("lib")
    with lib.active_fileset("models"):
        lib.add_file("test.lib")
    assert lib.add_asic_libcornerfileset("slow", "nldm", "models")
    assert lib.get("asic", "libcornerfileset", "slow", "nldm") == ["models"]


def test_add_asic_libcornerfileset_missing_fileset():
    with pytest.raises(LookupError, match="models is not defined in lib"):
        StdCellLibrary("lib").add_asic_libcornerfileset("slow", "nldm", "models")


def test_add_asic_libcornerfileset_invalid_model():
    with pytest.raises(TypeError, match="model must be a string"):
        StdCellLibrary("lib").add_asic_libcornerfileset("slow", 8, "models")


def test_add_asic_libcornerfileset_invalid_fileset():
    with pytest.raises(TypeError, match="fileset must be a string"):
        StdCellLibrary("lib").add_asic_libcornerfileset("slow", "nldm", 8)


def test_add_asic_pexcornerfileset():
    lib = StdCellLibrary("lib")
    with lib.active_fileset("models"):
        lib.add_file("test.sp")
        assert lib.add_asic_pexcornerfileset("slow")
    assert lib.get("asic", "pexcornerfileset", "slow") == ["models"]


def test_add_asic_pexcornerfileset_multiple():
    lib = StdCellLibrary("lib")
    with lib.active_fileset("models1"):
        lib.add_file("test.sp")
        assert lib.add_asic_pexcornerfileset("slow")
    with lib.active_fileset("models2"):
        lib.add_file("test.sp")
        assert lib.add_asic_pexcornerfileset("slow")
    assert lib.get("asic", "pexcornerfileset", "slow") == ["models1", "models2"]


def test_add_asic_pexcornerfileset_without_active():
    lib = StdCellLibrary("lib")
    with lib.active_fileset("models"):
        lib.add_file("test.sp")
    assert lib.add_asic_pexcornerfileset("slow", "models")
    assert lib.get("asic", "pexcornerfileset", "slow") == ["models"]


def test_add_asic_pexcornerfileset_missing_fileset():
    with pytest.raises(LookupError, match="models is not defined"):
        StdCellLibrary("lib").add_asic_pexcornerfileset("slow", "models")


def test_add_asic_pexcornerfileset_invalid_fileset():
    with pytest.raises(TypeError, match="fileset must be a string"):
        StdCellLibrary("lib").add_asic_pexcornerfileset("slow", 8)


def test_add_asic_aprfileset():
    lib = StdCellLibrary("lib")
    with lib.active_fileset("models"):
        lib.add_file("test.lef")
        assert lib.add_asic_aprfileset()
    assert lib.get("asic", "aprfileset") == ["models"]


def test_add_asic_aprfileset_multiple():
    lib = StdCellLibrary("lib")
    with lib.active_fileset("models1"):
        lib.add_file("test.lef")
        assert lib.add_asic_aprfileset()
    with lib.active_fileset("models2"):
        lib.add_file("test.gds")
        assert lib.add_asic_aprfileset()
    assert lib.get("asic", "aprfileset") == ["models1", "models2"]


def test_add_asic_aprfileset_without_active():
    lib = StdCellLibrary("lib")
    with lib.active_fileset("models"):
        lib.add_file("test.lef")
    assert lib.add_asic_aprfileset("models")
    assert lib.get("asic", "aprfileset") == ["models"]


def test_add_asic_aprfileset_missing_fileset():
    with pytest.raises(LookupError, match="models is not defined"):
        StdCellLibrary("lib").add_asic_aprfileset("models")


def test_add_asic_aprfileset_invalid_fileset():
    with pytest.raises(TypeError, match="fileset must be a string"):
        StdCellLibrary("lib").add_asic_aprfileset(8)


def test_add_asic_celllist():
    lib = StdCellLibrary("lib")
    lib.add_asic_celllist("dontuse", "*X0*")
    lib.add_asic_celllist("dontuse", "*X1*")
    assert lib.get("asic", "cells", "dontuse") == ["*X0*", "*X1*"]


def test_add_asic_site():
    lib = StdCellLibrary("lib")
    lib.add_asic_site("sc7p5site")
    assert lib.get("asic", "site") == ["sc7p5site"]


def test_add_asic_pdk():
    lib = StdCellLibrary("lib")
    pdk = PDK("test")
    pdk.set_stackup("10M")
    lib.add_asic_pdk(pdk)
    assert lib.get("asic", "pdk") == "test"
    assert lib.get("asic", "stackup") == ["10M"]


def test_add_asic_pdk_notdefault():
    lib = StdCellLibrary("lib")
    pdk = PDK("test")
    lib.add_asic_pdk(pdk, default=False)
    assert lib.get("asic", "pdk") is None


def test_add_asic_pdk_string():
    lib = StdCellLibrary("lib")
    lib.add_asic_pdk("test")
    assert lib.get("asic", "pdk") == "test"


def test_add_asic_pdk_string_not_default():
    lib = StdCellLibrary("lib")
    with pytest.raises(TypeError, match="pdk must be a PDK object"):
        lib.add_asic_pdk("test", default=False)
    assert lib.get("asic", "pdk") is None


def test_add_asic_pdk_string_invalid():
    lib = StdCellLibrary("lib")
    with pytest.raises(TypeError, match="pdk must be a PDK object or string"):
        lib.add_asic_pdk(1)


def test_add_asic_stackup():
    lib = StdCellLibrary("lib")
    lib.add_asic_stackup("10M")
    assert lib.get("asic", "stackup") == ["10M"]
    lib.add_asic_stackup("11M")
    assert lib.get("asic", "stackup") == ["10M", "11M"]
