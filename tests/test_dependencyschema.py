import graphviz
import logging
import pytest

import os.path

from unittest.mock import patch

from siliconcompiler.schema import NamedSchema, BaseSchema
from siliconcompiler.schema import EditableSchema, Parameter
from siliconcompiler.dependencyschema import DependencySchema


def test_init():
    schema = DependencySchema()
    assert schema.getkeys() == tuple(["deps", "package"])
    assert schema.get("deps") == []


def test_add_dep_invalid():
    schema = DependencySchema()

    with pytest.raises(TypeError,
                       match="Cannot add an object of type: <class "
                       "'siliconcompiler.schema.baseschema.BaseSchema'>"):
        schema.add_dep(BaseSchema())


def test_add_dep():
    schema = DependencySchema()

    dep = NamedSchema("thisname")
    assert schema.add_dep(dep)
    assert schema.get_dep("thisname") is dep
    assert schema.get("deps") == ["thisname"]
    assert schema.get("deps", field="lock") is True


def test_add_dep_confirm_reset():
    class Test(NamedSchema):
        def __init__(self):
            super().__init__("thisname")
            self.state_info = "notthis"

        def _reset(self):
            super()._reset()
            self.state_info = None

    schema = DependencySchema()

    dep = Test()
    assert dep.state_info == "notthis"
    assert schema.add_dep(dep)
    assert dep.state_info is None


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


def test_get_dep_not_found():
    schema = DependencySchema()

    with pytest.raises(KeyError, match="notthere is not an imported module"):
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


def test_get_dep_empty():
    assert DependencySchema().get_dep() == []


def test_get_dep():
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            NamedSchema.__init__(self, name)
            DependencySchema.__init__(self)

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
            NamedSchema.__init__(self, name)
            DependencySchema.__init__(self)

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
            NamedSchema.__init__(self, name)
            DependencySchema.__init__(self)

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
            NamedSchema.__init__(self, name)
            DependencySchema.__init__(self)

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


def test_get_dep_circle():
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            NamedSchema.__init__(self, name)
            DependencySchema.__init__(self)

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
            NamedSchema.__init__(self, name)
            DependencySchema.__init__(self)

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

        with pytest.raises(RuntimeError, match="Unable to save flowgraph: failed to execute"):
            schema.write_depgraph("test.png")
        render.assert_called_once()


def test_write_depgraph():
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            NamedSchema.__init__(self, name)
            DependencySchema.__init__(self)

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


def test_write_depgraph_alt_config():
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            NamedSchema.__init__(self, name)
            DependencySchema.__init__(self)

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


def test_write_depgraph_repeats():
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            NamedSchema.__init__(self, name)
            DependencySchema.__init__(self)

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


def test_write_depgraph_circle():
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            NamedSchema.__init__(self, name)
            DependencySchema.__init__(self)

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
        def __init__(self, name):
            NamedSchema.__init__(self, name)
            DependencySchema.__init__(self)

    schema = Test("top")

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.add_dep(dep10)
    assert dep01.add_dep(dep11)

    assert schema.add_dep(dep00)
    assert schema.add_dep(dep01)

    check = Test.from_manifest("test", cfg=schema.getdict())
    assert check.get_dep() == []
    module_map = {obj.name(): obj for obj in schema.get_dep()}
    check._populate_deps(module_map)
    assert check.get_dep() == schema.get_dep()


def test_populate_deps_missing():
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            NamedSchema.__init__(self, name)
            DependencySchema.__init__(self)

    schema = Test("top")

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.add_dep(dep10)
    assert dep01.add_dep(dep11)

    assert schema.add_dep(dep00)
    assert schema.add_dep(dep01)

    check = Test.from_manifest("test", cfg=schema.getdict())
    with pytest.raises(ValueError, match="level0-0 not available in map"):
        check._populate_deps({})


def test_populate_deps_already_populated():
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            NamedSchema.__init__(self, name)
            DependencySchema.__init__(self)

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
    module_map = {obj.name(): obj for obj in schema.get_dep()}
    check._populate_deps(module_map)
    assert check.get_dep() == [dep00, dep10]


def test_get_registered_sources():
    schema = DependencySchema()
    assert schema.getkeys("package") == tuple([])


def test_register_source():
    schema = DependencySchema()
    schema.register_source("testsource", "file://.")
    assert schema.get("package", "testsource", "root") == "file://."
    assert schema.get("package", "testsource", "tag") is None


def test_register_source_overwrite():
    schema = DependencySchema()
    schema.register_source("testsource", "file://.")
    schema.register_source("testsource", "file://test")
    assert schema.get("package", "testsource", "root") == "file://test"
    assert schema.get("package", "testsource", "tag") is None


def test_register_source_with_ref():
    schema = DependencySchema()
    schema.register_source("testsource", "file://.", "ref")
    assert schema.get("package", "testsource", "root") == "file://."
    assert schema.get("package", "testsource", "tag") == "ref"


def test_register_source_with_file():
    schema = DependencySchema()
    with open("test.txt", "w") as f:
        f.write("test")

    schema.register_source("testsource", "test.txt")
    assert schema.get("package", "testsource", "root") == os.path.abspath(".")
    assert schema.get("package", "testsource", "tag") is None


def test_find_files():
    class Test(DependencySchema):
        def __init__(self):
            super().__init__()

            schema = EditableSchema(self)
            schema.insert("file", Parameter("file"))

    test = Test()
    test.register_source("testsource", "file://.")
    param = test.set("file", "test.txt")
    param.set("testsource", field="package")

    with open("test.txt", "w") as f:
        f.write("test")

    assert test.find_files("file") == os.path.abspath("test.txt")


def test_find_files_no_source():
    class Test(DependencySchema):
        def __init__(self):
            super().__init__()

            schema = EditableSchema(self)
            schema.insert("file", Parameter("file"))

    test = Test()
    param = test.set("file", "test.txt")
    param.set("testsource", field="package")

    with pytest.raises(ValueError, match="Resolver for testsource not provided"):
        test.find_files("file")


def test_find_files_dir():
    class Test(DependencySchema):
        def __init__(self):
            super().__init__()

            schema = EditableSchema(self)
            schema.insert("dir", Parameter("dir"))

    test = Test()
    test.register_source("testsource", "file://.")
    param = test.set("dir", "test")
    param.set("testsource", field="package")

    os.makedirs("test", exist_ok=True)

    assert test.find_files("dir") == os.path.abspath("test")


def test_find_files_no_sources():
    class Test(DependencySchema):
        def __init__(self):
            super().__init__()

            schema = EditableSchema(self)
            schema.insert("dir", Parameter("dir"))

    test = Test()
    assert test.set("dir", "test")

    os.makedirs("test", exist_ok=True)

    assert test.find_files("dir") == os.path.abspath("test")


def test_find_files_cwd():
    class Test(DependencySchema):
        def __init__(self):
            super().__init__()

            schema = EditableSchema(self)
            schema.insert("dir", Parameter("dir"))

    test = Test()
    assert test.set("dir", "test")

    os.makedirs("cwd/test", exist_ok=True)

    assert test.find_files("dir", cwd="cwd") == os.path.abspath("cwd/test")


def test_find_files_keypath():
    class Test(DependencySchema):
        def __init__(self):
            super().__init__()

            schema = EditableSchema(self)
            schema.insert("file", Parameter("file"))
            schema.insert("ref", Parameter("dir"))

    class Root(BaseSchema):
        def __init__(self):
            super().__init__()

            schema = EditableSchema(self)
            schema.insert("ref", Parameter("dir"))
            schema.insert("test", Test())

    root = Root()
    test = root.get("test", field="schema")
    test.register_source("keyref", "key://ref")
    assert root.set("ref", "test")
    os.makedirs("test", exist_ok=True)
    param = test.set("file", "test.txt")
    param.set("keyref", field="package")

    with open("test/test.txt", "w") as f:
        f.write("test")

    assert test.find_files("file", runnable=root) == os.path.abspath("test/test.txt")


def test_find_source():
    schema = DependencySchema()
    schema.register_source("testsource", "file://.")
    assert schema.find_source("testsource") == os.path.abspath(".")


def test_find_source_not_found():
    schema = DependencySchema()
    with pytest.raises(ValueError, match="testsource is not a recognized source"):
        schema.find_source("testsource")


def test_find_source_keypath():
    class Test(DependencySchema):
        def __init__(self):
            super().__init__()

            schema = EditableSchema(self)
            schema.insert("file", Parameter("file"))
            schema.insert("ref", Parameter("dir"))

    class Root(BaseSchema):
        def __init__(self):
            super().__init__()

            schema = EditableSchema(self)
            schema.insert("ref", Parameter("dir"))
            schema.insert("test", Test())

    root = Root()
    test = root.get("test", field="schema")
    test.register_source("keyref", "key://ref")
    assert root.set("ref", "test")
    os.makedirs("test", exist_ok=True)

    assert test.find_source("keyref", runnable=root) == os.path.abspath("test")


def test_check_filepaths_empty():
    schema = DependencySchema()
    edit = EditableSchema(schema)
    param = Parameter("[dir]")
    edit.insert("directory", param)

    assert schema.check_filepaths() is True


def test_check_filepaths_found():
    schema = DependencySchema()
    edit = EditableSchema(schema)
    param = Parameter("[dir]")
    edit.insert("directory", param)

    os.makedirs("test0", exist_ok=True)

    assert schema.set("directory", "test0")

    assert schema.check_filepaths() is True


def test_check_filepaths_not_found_no_logger():
    schema = DependencySchema()
    edit = EditableSchema(schema)
    param = Parameter("[dir]")
    edit.insert("directory", param)

    assert schema.set("directory", "test0")

    assert schema.check_filepaths() is False


def test_check_filepaths_not_found_logger(caplog):
    schema = DependencySchema()
    edit = EditableSchema(schema)
    param = Parameter("[dir]")
    edit.insert("directory", param)

    assert schema.set("directory", "test0")

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    assert schema.check_filepaths(logger=logger) is False
    assert "Parameter [directory] path test0 is invalid" in caplog.text
