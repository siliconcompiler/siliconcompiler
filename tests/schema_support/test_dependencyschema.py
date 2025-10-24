import graphviz
import pytest

import os.path

from unittest.mock import patch

from siliconcompiler.schema import NamedSchema, BaseSchema
from siliconcompiler.schema_support.dependencyschema import DependencySchema
from siliconcompiler.schema_support.pathschema import PathSchemaSimpleBase, PathSchema


def test_init():
    schema = DependencySchema()
    assert schema.getkeys() == ("deps",)
    assert schema.get("deps") == []


def test_add_dep_invalid():
    schema = DependencySchema()

    with pytest.raises(TypeError,
                       match=r"^Cannot add an object of type: <class "
                       r"'siliconcompiler\.schema\.baseschema\.BaseSchema'>$"):
        schema.add_dep(BaseSchema())


def test_add_dep():
    schema = DependencySchema()

    dep = NamedSchema("thisname")
    assert schema.add_dep(dep)
    assert schema.get_dep("thisname") is dep
    assert schema.get("deps") == ["thisname"]
    assert schema.get("deps", field="lock") is True


def test_has_dep():
    schema = DependencySchema()

    assert schema.has_dep("thisname") is False
    assert schema.add_dep(NamedSchema("thisname"))
    assert schema.has_dep("thisname") is True


def test_has_dep_with_object():
    schema = DependencySchema()

    dep = NamedSchema("thisname")
    assert schema.has_dep("thisname") is False
    assert schema.add_dep(dep)
    assert schema.has_dep(dep) is True


def test_has_dep_invalid():
    schema = DependencySchema()

    assert schema.has_dep(1) is False
    assert schema.has_dep(BaseSchema()) is False
    assert schema.has_dep(NamedSchema) is False


def test_add_dep_clobber():
    schema = DependencySchema()

    dep0 = NamedSchema("thisname")
    dep1 = NamedSchema("thisname")
    assert schema.add_dep(dep0)
    assert schema.get_dep("thisname") is dep0
    assert schema.add_dep(dep1, clobber=True)
    assert schema.get_dep("thisname") is dep1
    assert schema.get("deps") == ["thisname"]


def test_add_dep_no_clobber():
    schema = DependencySchema()

    dep0 = NamedSchema("thisname")
    dep1 = NamedSchema("thisname")
    assert schema.add_dep(dep0)
    assert schema.get_dep("thisname") is dep0
    assert schema.add_dep(dep1, clobber=False) is False
    assert schema.get_dep("thisname") is dep0
    assert schema.get("deps") == ["thisname"]


def test_add_dep_unnamed():
    schema = DependencySchema()

    with pytest.raises(ValueError, match="^Cannot add an unnamed dependency$"):
        schema.add_dep(NamedSchema())


def test_get_dep_not_found():
    schema = DependencySchema()

    with pytest.raises(KeyError, match="^'notthere is not an imported module'$"):
        schema.get_dep("notthere")


def test_remove_dep_not_there():
    schema = DependencySchema()
    assert schema.remove_dep("notthere") is False


def test_remove_dep():
    schema = DependencySchema()
    schema.add_dep(NamedSchema("thisname"))
    assert schema.get_dep("thisname")
    assert schema.remove_dep("thisname") is True
    assert schema.get("deps", field="lock") is True
    assert schema.get_dep() == []
    assert schema.get("deps") == []


def test_remove_dep_with_object():
    schema = DependencySchema()
    dep = NamedSchema("thisname")
    schema.add_dep(dep)
    assert schema.get_dep("thisname")
    assert schema.remove_dep(dep) is True
    assert schema.get("deps", field="lock") is True
    assert schema.get_dep() == []
    assert schema.get("deps") == []


def test_get_dep_empty():
    assert DependencySchema().get_dep() == []


def test_get_dep():
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            super().__init__()
            self.set_name(name)

    schema = DependencySchema()

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.add_dep(dep10)
    assert dep01.add_dep(dep11)

    assert schema.add_dep(dep00)
    assert schema.add_dep(dep01)

    assert schema.get_dep() == [dep00, dep10, dep01, dep11]


def test_get_dep_no_hier():
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            super().__init__()
            self.set_name(name)

    schema = DependencySchema()

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.add_dep(dep10)
    assert dep01.add_dep(dep11)

    assert schema.add_dep(dep00)
    assert schema.add_dep(dep01)

    assert schema.get_dep(hierarchy=False) == [dep00, dep01]


def test_get_dep_repeats():
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            super().__init__()
            self.set_name(name)

    schema = DependencySchema()

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.add_dep(dep10)
    assert dep00.add_dep(dep11)
    assert dep01.add_dep(dep11)

    assert schema.add_dep(dep00)
    assert schema.add_dep(dep01)

    assert schema.get_dep() == [dep00, dep10, dep11, dep01]


def test_get_dep_non_dep():
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            super().__init__()
            self.set_name(name)

    schema = DependencySchema()

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")
    dep20 = NamedSchema("level2-0")
    dep21 = NamedSchema("level2-1")

    assert dep00.add_dep(dep10)
    assert dep10.add_dep(dep20)
    assert dep01.add_dep(dep11)
    assert dep11.add_dep(dep21)

    assert schema.add_dep(dep00)
    assert schema.add_dep(dep01)

    assert schema.get_dep() == \
        [dep00, dep10, dep20, dep01, dep11, dep21]


def test_get_dep_hier():
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            super().__init__()
            self.set_name(name)

    schema = DependencySchema()

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep02 = Test("level0-2")

    assert dep00.add_dep(dep01)
    assert dep01.add_dep(dep02)

    assert schema.add_dep(dep00)

    assert schema.get_dep("level0-0") is dep00
    assert schema.get_dep("level0-0.level0-1") is dep01
    assert schema.get_dep("level0-0.level0-1.level0-2") is dep02


def test_get_dep_hier_with_non_dep():
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            super().__init__()
            self.set_name(name)

    schema = DependencySchema()

    dep00 = Test("level0-0")
    dep01 = NamedSchema("level0-1")

    assert dep00.add_dep(dep01)

    assert schema.add_dep(dep00)

    assert schema.get_dep("level0-0") is dep00
    assert schema.get_dep("level0-0.level0-1") is dep01

    with pytest.raises(KeyError,
                       match=r"^'level0-1\.notthis does not contain dependency information'$"):
        schema.get_dep("level0-0.level0-1.notthis")


def test_get_dep_circle():
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            super().__init__()
            self.set_name(name)

    schema = DependencySchema()

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.add_dep(dep10)
    assert dep10.add_dep(dep01)
    assert dep01.add_dep(dep11)
    assert dep11.add_dep(dep00)

    assert schema.add_dep(dep00)

    assert schema.get_dep() == [dep00, dep10, dep01, dep11]


def test_write_depgraph_no_graphviz_exe():
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            super().__init__()
            self.set_name(name)

    schema = Test("top")

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.add_dep(dep10)
    assert dep01.add_dep(dep11)

    assert schema.add_dep(dep00)
    assert schema.add_dep(dep01)

    with patch("graphviz.Digraph.render") as render:
        def raise_error(*args, **kwargs):
            raise graphviz.ExecutableNotFound("args")
        render.side_effect = raise_error

        with pytest.raises(RuntimeError,
                           match="^Unable to save flowgraph: failed to execute 'a', make sure the "
                                 "Graphviz executables are on your systems' PATH$"):
            schema.write_depgraph("test.png")
        render.assert_called_once()


def test_write_depgraph(has_graphviz):
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            super().__init__()
            self.set_name(name)

    schema = Test("top")

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.add_dep(dep10)
    assert dep01.add_dep(dep11)

    assert schema.add_dep(dep00)
    assert schema.add_dep(dep01)

    schema.write_depgraph("test.png")
    assert os.path.exists("test.png")


def test_write_depgraph_alt_config(has_graphviz):
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            super().__init__()
            self.set_name(name)

    schema = Test("top")

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.add_dep(dep10)
    assert dep01.add_dep(dep11)

    assert schema.add_dep(dep00)
    assert schema.add_dep(dep01)

    schema.write_depgraph("test.png", landscape=True, border=False)
    assert os.path.exists("test.png")


def test_write_depgraph_repeats(has_graphviz):
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            super().__init__()
            self.set_name(name)

    schema = Test("top")

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.add_dep(dep10)
    assert dep00.add_dep(dep11)
    assert dep01.add_dep(dep11)

    assert schema.add_dep(dep00)
    assert schema.add_dep(dep01)

    schema.write_depgraph("test.png")
    assert os.path.exists("test.png")


def test_write_depgraph_circle(has_graphviz):
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            super().__init__()
            self.set_name(name)

    schema = Test("top")

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.add_dep(dep10)
    assert dep10.add_dep(dep01)
    assert dep01.add_dep(dep11)
    assert dep11.add_dep(dep00)

    assert schema.add_dep(dep00)

    schema.write_depgraph("test.png")
    assert os.path.exists("test.png")


def test_populate_deps_empty():
    schema = DependencySchema()
    schema._populate_deps({})


def test_populate_deps():
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name=None):
            super().__init__()
            self.set_name(name)

    schema = Test("top")

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.add_dep(dep10)
    assert dep01.add_dep(dep11)

    assert schema.add_dep(dep00)
    assert schema.add_dep(dep01)

    check = Test.from_manifest(name="test", cfg=schema.getdict())
    assert check.get_dep() == []
    module_map = {obj.name: obj for obj in schema.get_dep()}
    check._populate_deps(module_map)
    assert check.get_dep() == schema.get_dep()


def test_populate_deps_missing():
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name=None):
            super().__init__()
            self.set_name(name)

    schema = Test("top")

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.add_dep(dep10)
    assert dep01.add_dep(dep11)

    assert schema.add_dep(dep00)
    assert schema.add_dep(dep01)

    check = Test.from_manifest(name="test", cfg=schema.getdict())
    with pytest.raises(ValueError, match="^level0-0 not available in map$"):
        check._populate_deps({})


def test_populate_deps_already_populated():
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            super().__init__()
            self.set_name(name)

    schema = Test("top")

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.add_dep(dep10)
    assert dep01.add_dep(dep11)

    assert schema.add_dep(dep00)
    assert schema.add_dep(dep01)

    check = Test("top")
    check.add_dep(dep00)

    assert check.get_dep() == [dep00, dep10]
    module_map = {obj.name: obj for obj in schema.get_dep()}
    check._populate_deps(module_map)
    assert check.get_dep() == [dep00, dep10]


def test_check_filepaths_none():
    assert DependencySchema().check_filepaths() is True


@pytest.mark.parametrize("pcls", (PathSchemaSimpleBase, PathSchema))
def test_check_filepaths_self(pcls):
    class Test(DependencySchema, pcls):
        pass

    with patch("siliconcompiler.schema_support.pathschema.PathSchemaBase.check_filepaths") as cf:
        cf.return_value = True
        assert Test().check_filepaths() is True
        cf.assert_called_once()


@pytest.mark.parametrize("pcls", (PathSchemaSimpleBase, PathSchema))
def test_check_filepaths_self_fail(pcls):
    class Test(DependencySchema, pcls):
        pass

    with patch("siliconcompiler.schema_support.pathschema.PathSchemaBase.check_filepaths") as cf:
        cf.return_value = False
        assert Test().check_filepaths() is False
        cf.assert_called_once()


def test_check_filepaths_depth_fail():
    class Test(DependencySchema, PathSchema):
        pass

    class TestDepth(NamedSchema, DependencySchema, PathSchema):
        pass

    dut = Test()
    dep = TestDepth("testdepth0")
    dep.add_dep(TestDepth("testdepth1"))
    dut.add_dep(dep)

    with patch("siliconcompiler.schema_support.pathschema.PathSchemaBase.check_filepaths") as cf:
        cf.return_value = False
        assert dut.check_filepaths() is False
        assert cf.call_count == 3


def test_check_filepaths_depth_pass():
    class Test(DependencySchema, PathSchema):
        pass

    class TestDepth(NamedSchema, DependencySchema, PathSchema):
        pass

    dut = Test()
    dep = TestDepth("testdepth0")
    dep.add_dep(TestDepth("testdepth1"))
    dut.add_dep(dep)

    with patch("siliconcompiler.schema_support.pathschema.PathSchemaBase.check_filepaths") as cf:
        cf.return_value = True
        assert dut.check_filepaths() is True
        assert cf.call_count == 3


def test_check_filepaths_depth_partial():
    class Test(DependencySchema, PathSchema):
        pass

    class TestDepth(NamedSchema, DependencySchema, PathSchema):
        pass

    dut = Test()
    dep = TestDepth("testdepth0")
    dep.add_dep(TestDepth("testdepth1"))
    dut.add_dep(dep)

    def cf_call(obj):
        try:
            if obj.name == "testdepth1":
                return False
        except:  # noqa E722
            pass
        return True

    with patch("siliconcompiler.schema_support.pathschema.PathSchemaBase.check_filepaths") as cf:
        cf.side_effect = cf_call
        assert dut.check_filepaths() is False
        assert cf.call_count == 3
