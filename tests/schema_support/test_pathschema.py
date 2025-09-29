import logging
import pytest

import os.path

from pathlib import Path
from unittest.mock import patch

from siliconcompiler import Project, Design
from siliconcompiler.schema import BaseSchema
from siliconcompiler.schema import EditableSchema, Parameter
from siliconcompiler.schema_support.pathschema import PathSchemaBase, PathSchema, \
    PathSchemaSimpleBase


def test_init():
    schema = PathSchema()
    assert schema.getkeys() == ("dataroot",)


def test_get_registered_sources():
    schema = PathSchema()
    assert schema.getkeys("dataroot") == tuple([])


def test_set_dataroot():
    schema = PathSchema()
    schema.set_dataroot("testsource", "file://.")
    assert schema.get("dataroot", "testsource", "path") == "file://."
    assert schema.get("dataroot", "testsource", "tag") is None


def test_set_dataroot_overwrite():
    schema = PathSchema()
    schema.set_dataroot("testsource", "file://.")
    schema.set_dataroot("testsource", "file://test")
    assert schema.get("dataroot", "testsource", "path") == "file://test"
    assert schema.get("dataroot", "testsource", "tag") is None


def test_set_dataroot_with_ref():
    schema = PathSchema()
    schema.set_dataroot("testsource", "file://.", "ref")
    assert schema.get("dataroot", "testsource", "path") == "file://."
    assert schema.get("dataroot", "testsource", "tag") == "ref"


def test_set_dataroot_with_file():
    schema = PathSchema()
    with open("test.txt", "w") as f:
        f.write("test")

    schema.set_dataroot("testsource", "test.txt")
    assert schema.get("dataroot", "testsource", "path") == os.path.abspath(".")
    assert schema.get("dataroot", "testsource", "tag") is None


def test_find_files():
    class Test(PathSchema):
        def __init__(self):
            super().__init__()

            schema = EditableSchema(self)
            schema.insert("file", Parameter("file"))

    test = Test()
    test.set_dataroot("testsource", "file://.")
    param = test.set("file", "test.txt")
    param.set("testsource", field="package")

    with open("test.txt", "w") as f:
        f.write("test")

    assert test.find_files("file") == os.path.abspath("test.txt")


def test_find_files_no_source():
    class Test(PathSchema):
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
    class Test(PathSchema):
        def __init__(self):
            super().__init__()

            schema = EditableSchema(self)
            schema.insert("dir", Parameter("dir"))

    test = Test()
    test.set_dataroot("testsource", "file://.")
    param = test.set("dir", "test")
    param.set("testsource", field="package")

    os.makedirs("test", exist_ok=True)

    assert test.find_files("dir") == os.path.abspath("test")


def test_find_files_no_sources():
    class Test(PathSchema):
        def __init__(self):
            super().__init__()

            schema = EditableSchema(self)
            schema.insert("dir", Parameter("dir"))

    test = Test()
    assert test.set("dir", "test")

    os.makedirs("test", exist_ok=True)

    assert test.find_files("dir") == os.path.abspath("test")


def test_find_files_cwd(monkeypatch):
    class Test(PathSchemaBase):
        def __init__(self):
            super().__init__()

            schema = EditableSchema(self)
            schema.insert("dir", Parameter("dir"))

    test = Project(Design("testdesign"))
    EditableSchema(test).insert("test", Test())
    monkeypatch.setattr(test, "_Project__cwd", "cwd")

    assert test.set("test", "dir", "test")

    os.makedirs("cwd/test", exist_ok=True)

    assert test.find_files("test", "dir") == os.path.abspath("cwd/test")


def test_find_files_collectiondir():
    class Test(Project):
        def __init__(self):
            super().__init__(Design("testdesign"))

            t = PathSchemaBase()
            schema = EditableSchema(t)
            schema.insert("dir", Parameter("dir"))

            schema = EditableSchema(self)
            schema.insert("test", t)

    test = Test()
    assert test.set("test", "dir", "test")

    os.makedirs("collect/test_3a52ce780950d4d969792a2559cd519d7ee8c727", exist_ok=True)

    with patch("siliconcompiler.schema_support.pathschema.collectiondir") as collect:
        collect.return_value = os.path.abspath("collect")
        assert test.find_files("test", "dir") == \
            os.path.abspath("collect/test_3a52ce780950d4d969792a2559cd519d7ee8c727")
        collect.assert_called_once()


def test_find_files_keypath():
    class Test(PathSchema):
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
    test.set_dataroot("keyref", "key://ref")
    assert root.set("ref", "test")
    os.makedirs("test", exist_ok=True)
    param = test.set("file", "test.txt")
    param.set("keyref", field="package")

    with open("test/test.txt", "w") as f:
        f.write("test")

    assert test.find_files("file") == os.path.abspath("test/test.txt")


def test_get_dataroot():
    schema = PathSchema()
    schema.set_dataroot("testsource", "file://.")
    assert schema.get_dataroot("testsource") == os.path.abspath(".")


def test_get_dataroot_not_found():
    schema = PathSchema()
    with pytest.raises(ValueError, match="testsource is not a recognized source"):
        schema.get_dataroot("testsource")


def test_get_dataroot_keypath():
    class Test(PathSchema):
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
    test.set_dataroot("keyref", "key://ref")
    assert root.set("ref", "test")
    os.makedirs("test", exist_ok=True)

    assert test.get_dataroot("keyref") == os.path.abspath("test")


def test_check_filepaths_empty():
    schema = PathSchemaBase()
    edit = EditableSchema(schema)
    param = Parameter("[dir]")
    edit.insert("directory", param)

    assert schema.check_filepaths() is True


def test_check_filepaths_found():
    schema = PathSchemaBase()
    edit = EditableSchema(schema)
    param = Parameter("[dir]")
    edit.insert("directory", param)

    os.makedirs("test0", exist_ok=True)

    assert schema.set("directory", "test0")

    assert schema.check_filepaths() is True


def test_check_filepaths_not_found_no_logger():
    schema = PathSchemaBase()
    edit = EditableSchema(schema)
    param = Parameter("[dir]")
    edit.insert("directory", param)

    assert schema.set("directory", "test0")

    assert schema.check_filepaths() is False


def test_check_filepaths_not_found_logger(caplog):
    schema = PathSchemaBase()
    edit = EditableSchema(schema)
    param = Parameter("[dir]")
    edit.insert("directory", param)

    assert schema.set("directory", "test0")

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    schema.logger = logger

    assert schema.check_filepaths() is False
    assert "Parameter [directory] path test0 is invalid" in caplog.text


def test_check_filepaths_cwd(monkeypatch):
    class Test(PathSchemaSimpleBase):
        def __init__(self):
            super().__init__()

            schema = EditableSchema(self)
            schema.insert("dir", Parameter("dir"))

    test = Project(Design("testdesign"))
    EditableSchema(test).insert("test", Test())
    monkeypatch.setattr(test, "_Project__cwd", "cwd")

    assert test.set("test", "dir", "test")

    os.makedirs("cwd/test", exist_ok=True)

    assert test.get("test", field="schema").check_filepaths() is True


def test_check_filepaths_collectiondir():
    class Test(Project):
        def __init__(self):
            super().__init__(Design("testdesign"))

            t = PathSchemaBase()
            schema = EditableSchema(t)
            schema.insert("dir", Parameter("dir"))

            schema = EditableSchema(self)
            schema.insert("test", t)

    test = Test()
    assert test.set("test", "dir", "test")

    os.makedirs("collect/test_3a52ce780950d4d969792a2559cd519d7ee8c727", exist_ok=True)

    with patch("siliconcompiler.schema_support.pathschema.collectiondir") as collect:
        collect.return_value = os.path.abspath("collect")
        assert test.get("test", field="schema").check_filepaths() is True
        collect.assert_called_once()


def test_active_dataroot():
    schema = PathSchema()

    schema.set_dataroot("testpack", __file__)

    assert schema._get_active(None) is None
    with schema.active_dataroot("testpack"):
        assert schema._get_active(None) == {
            "package": "testpack"
        }
        assert schema._get_active("package") == "testpack"
    assert schema._get_active(None) is None


def test_active_dataroot_missing():
    schema = PathSchema()

    assert schema._get_active(None) is None
    with pytest.raises(ValueError, match="testpack is not a recognized dataroot"):
        with schema.active_dataroot("testpack"):
            pass
    assert schema._get_active(None) is None


def test_simple_find_files():
    class Test(PathSchema, PathSchemaSimpleBase):
        def __init__(self):
            super().__init__()

            schema = EditableSchema(self)
            schema.insert("file", Parameter("file"))

    test = Test()
    test.set_dataroot("testsource", "file://.")
    param = test.set("file", "test.txt")
    param.set("testsource", field="package")

    with open("test.txt", "w") as f:
        f.write("test")

    assert test.find_files("file") == os.path.abspath("test.txt")


def test_simple_find_files_no_source():
    class Test(PathSchemaSimpleBase):
        def __init__(self):
            super().__init__()

            schema = EditableSchema(self)
            schema.insert("file", Parameter("file"))

    test = Test()
    param = test.set("file", "test.txt")
    param.set("testsource", field="package")

    with pytest.raises(ValueError, match="Resolver for testsource not provided"):
        test.find_files("file")


def test_simple_find_files_dir():
    class Test(PathSchema, PathSchemaSimpleBase):
        def __init__(self):
            super().__init__()

            schema = EditableSchema(self)
            schema.insert("dir", Parameter("dir"))

    test = Test()
    test.set_dataroot("testsource", "file://.")
    param = test.set("dir", "test")
    param.set("testsource", field="package")

    os.makedirs("test", exist_ok=True)

    assert test.find_files("dir") == os.path.abspath("test")


def test_simple_find_files_no_sources():
    class Test(PathSchemaSimpleBase):
        def __init__(self):
            super().__init__()

            schema = EditableSchema(self)
            schema.insert("dir", Parameter("dir"))

    test = Test()
    assert test.set("dir", "test")

    os.makedirs("test", exist_ok=True)

    assert test.find_files("dir") == os.path.abspath("test")


def test_simple_find_files_cwd(monkeypatch):
    class Test(PathSchemaSimpleBase):
        def __init__(self):
            super().__init__()

            schema = EditableSchema(self)
            schema.insert("dir", Parameter("dir"))

    test = Project(Design("testdesign"))
    EditableSchema(test).insert("test", Test())
    monkeypatch.setattr(test, "_Project__cwd", "cwd")

    assert test.set("test", "dir", "test")

    os.makedirs("cwd/test", exist_ok=True)

    assert test.find_files("test", "dir") == os.path.abspath("cwd/test")


def test_simple_find_files_collectiondir():
    class Test(Project):
        def __init__(self):
            super().__init__(Design("testdesign"))

            t = PathSchemaSimpleBase()
            schema = EditableSchema(t)
            schema.insert("dir", Parameter("dir"))

            schema = EditableSchema(self)
            schema.insert("test", t)

    test = Test()
    assert test.set("test", "dir", "test")

    os.makedirs("collect/test_3a52ce780950d4d969792a2559cd519d7ee8c727", exist_ok=True)

    with patch("siliconcompiler.schema_support.pathschema.collectiondir") as collect:
        collect.return_value = os.path.abspath("collect")
        assert test.find_files("test", "dir") == \
            os.path.abspath("collect/test_3a52ce780950d4d969792a2559cd519d7ee8c727")
        collect.assert_called_once()


def test_hash_files_file():
    schema = PathSchemaBase()
    edit = EditableSchema(schema)
    param = Parameter("file")
    edit.insert("file", param)

    with open("testfile.txt", "w") as f:
        f.write("test")

    assert schema.set("file", "testfile.txt")

    assert schema.hash_files("file") == \
        "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"


def test_hash_files_list_file():
    schema = PathSchemaBase()
    edit = EditableSchema(schema)
    param = Parameter("[file]")
    edit.insert("file", param)

    with open("testfile0.txt", "w") as f:
        f.write("test0")

    with open("testfile1.txt", "w") as f:
        f.write("test1")

    assert schema.set("file", ["testfile0.txt", "testfile1.txt"])

    assert schema.hash_files("file") == \
        [
            "590c9f8430c7435807df8ba9a476e3f1295d46ef210f6efae2043a4c085a569e",
            "1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014"
        ]


def test_hash_files_dir():
    schema = PathSchemaBase()
    edit = EditableSchema(schema)
    param = Parameter("dir")
    edit.insert("dir", param)

    Path("testpath").mkdir(exist_ok=True)

    with open("testpath/testfile.txt", "w") as f:
        f.write("test")

    assert schema.set("dir", "testpath")

    assert schema.hash_files("dir") == \
        "9fca19f3378585fc7800eaf99ae48169848baf0eedbb1b63c0bde3a0d6c2bf10"


def test_hash_files_list_dir():
    schema = PathSchemaBase()
    edit = EditableSchema(schema)
    param = Parameter("[dir]")
    edit.insert("dir", param)

    Path("testpath0").mkdir(exist_ok=True)
    Path("testpath1").mkdir(exist_ok=True)

    with open("testpath0/testfile.txt", "w") as f:
        f.write("test0")

    with open("testpath1/testfile.txt", "w") as f:
        f.write("test1")

    assert schema.set("dir", ["testpath0", "testpath1"])

    assert schema.hash_files("dir") == \
        [
            "0ebe9064753ebf28a96a7ef4bf6a2b707091acf7f0063566d1c339aeeb64c759",
            "c7e3c20a832a68749bd28d790d5fa1cbf5168a80fd38989f2cceefd8b1a69a46"
        ]


def test_get_active_dataroot_use_user():
    assert PathSchema()._get_active_dataroot("user") == "user"


@pytest.mark.parametrize("input", [None, ...])
def test_get_active_dataroot_use_none(input):
    assert PathSchema()._get_active_dataroot(input) is None


def test_get_active_dataroot_use_active():
    schema = PathSchema()
    schema.set_dataroot("active", "file://")

    with schema.active_dataroot("active"):
        assert schema._get_active_dataroot(None) == "active"


def test_get_active_dataroot_use_active_user():
    schema = PathSchema()
    schema.set_dataroot("active", "file://")

    with schema.active_dataroot("active"):
        assert schema._get_active_dataroot("user") == "user"


def test_get_active_dataroot_use_defined():
    schema = PathSchema()
    schema.set_dataroot("defined", "file://")

    assert schema._get_active_dataroot(None) == "defined"


def test_get_active_dataroot_multiple_defined():
    schema = PathSchema()
    schema.set_dataroot("defined0", "file://")
    schema.set_dataroot("defined1", "file://")

    with pytest.raises(ValueError,
                       match="dataroot must be specified, multiple are defined: "
                             "defined0, defined1"):
        schema._get_active_dataroot(None)


def test_dataroot_section_normal():
    schema_base = PathSchema()

    assert schema_base._PathSchema__dataroot_section() is schema_base


def test_dataroot_section_above():
    schema = PathSchema()
    EditableSchema(schema).remove("dataroot")

    schema_base = PathSchema()
    EditableSchema(schema_base).insert("test", schema)

    assert schema._PathSchema__dataroot_section() is schema_base


def test_dataroot_section_not_above():
    schema = PathSchema()
    schema_base = PathSchema()
    EditableSchema(schema_base).insert("test", schema)

    assert schema._PathSchema__dataroot_section() is schema


def test_dataroot_section_above_active():
    schema = PathSchema()
    EditableSchema(schema).remove("dataroot")

    schema_base = PathSchema()
    EditableSchema(schema_base).insert("test", schema)
    schema_base.set_dataroot("test", __file__)

    with schema.active_dataroot("test"):
        assert schema_base._get_active("package") is None
        assert schema._get_active("package") == "test"
