import logging
import pytest

import os.path

from siliconcompiler.schema import BaseSchema
from siliconcompiler.schema import EditableSchema, Parameter
from siliconcompiler.pathschema import PathSchema


def test_init():
    schema = PathSchema()
    assert schema.getkeys() == ("dataref",)


def test_get_registered_sources():
    schema = PathSchema()
    assert schema.getkeys("dataref") == tuple([])


def test_register_dataref():
    schema = PathSchema()
    schema.register_dataref("testsource", "file://.")
    assert schema.get("dataref", "testsource", "path") == "file://."
    assert schema.get("dataref", "testsource", "tag") is None


def test_register_dataref_overwrite():
    schema = PathSchema()
    schema.register_dataref("testsource", "file://.")
    schema.register_dataref("testsource", "file://test")
    assert schema.get("dataref", "testsource", "path") == "file://test"
    assert schema.get("dataref", "testsource", "tag") is None


def test_register_dataref_with_ref():
    schema = PathSchema()
    schema.register_dataref("testsource", "file://.", "ref")
    assert schema.get("dataref", "testsource", "path") == "file://."
    assert schema.get("dataref", "testsource", "tag") == "ref"


def test_register_dataref_with_file():
    schema = PathSchema()
    with open("test.txt", "w") as f:
        f.write("test")

    schema.register_dataref("testsource", "test.txt")
    assert schema.get("dataref", "testsource", "path") == os.path.abspath(".")
    assert schema.get("dataref", "testsource", "tag") is None


def test_find_files():
    class Test(PathSchema):
        def __init__(self):
            super().__init__()

            schema = EditableSchema(self)
            schema.insert("file", Parameter("file"))

    test = Test()
    test.register_dataref("testsource", "file://.")
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
    test.register_dataref("testsource", "file://.")
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


def test_find_files_cwd():
    class Test(PathSchema):
        cwd = "cwd"

        def __init__(self):
            super().__init__()

            schema = EditableSchema(self)
            schema.insert("dir", Parameter("dir"))

    test = Test()
    assert test.set("dir", "test")

    os.makedirs("cwd/test", exist_ok=True)

    assert test.find_files("dir") == os.path.abspath("cwd/test")


def test_find_files_collection_dir():
    class Test(PathSchema):
        calls = 0

        def collection_dir(self):
            self.calls += 1
            return os.path.abspath("collect")

        def __init__(self):
            super().__init__()

            schema = EditableSchema(self)
            schema.insert("dir", Parameter("dir"))

    test = Test()
    assert test.set("dir", "test")

    os.makedirs("collect/test_3a52ce780950d4d969792a2559cd519d7ee8c727", exist_ok=True)

    assert test.find_files("dir") == \
        os.path.abspath("collect/test_3a52ce780950d4d969792a2559cd519d7ee8c727")
    assert test.calls == 1


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
    test.register_dataref("keyref", "key://ref")
    assert root.set("ref", "test")
    os.makedirs("test", exist_ok=True)
    param = test.set("file", "test.txt")
    param.set("keyref", field="package")

    with open("test/test.txt", "w") as f:
        f.write("test")

    assert test.find_files("file") == os.path.abspath("test/test.txt")


def test_find_dataref():
    schema = PathSchema()
    schema.register_dataref("testsource", "file://.")
    assert schema.find_dataref("testsource") == os.path.abspath(".")


def test_find_dataref_not_found():
    schema = PathSchema()
    with pytest.raises(ValueError, match="testsource is not a recognized source"):
        schema.find_dataref("testsource")


def test_find_dataref_keypath():
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
    test.register_dataref("keyref", "key://ref")
    assert root.set("ref", "test")
    os.makedirs("test", exist_ok=True)

    assert test.find_dataref("keyref") == os.path.abspath("test")


def test_check_filepaths_empty():
    schema = PathSchema()
    edit = EditableSchema(schema)
    param = Parameter("[dir]")
    edit.insert("directory", param)

    assert schema.check_filepaths() is True


def test_check_filepaths_found():
    schema = PathSchema()
    edit = EditableSchema(schema)
    param = Parameter("[dir]")
    edit.insert("directory", param)

    os.makedirs("test0", exist_ok=True)

    assert schema.set("directory", "test0")

    assert schema.check_filepaths() is True


def test_check_filepaths_not_found_no_logger():
    schema = PathSchema()
    edit = EditableSchema(schema)
    param = Parameter("[dir]")
    edit.insert("directory", param)

    assert schema.set("directory", "test0")

    assert schema.check_filepaths() is False


def test_check_filepaths_not_found_logger(caplog):
    schema = PathSchema()
    edit = EditableSchema(schema)
    param = Parameter("[dir]")
    edit.insert("directory", param)

    assert schema.set("directory", "test0")

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    schema.logger = logger

    assert schema.check_filepaths() is False
    assert "Parameter [directory] path test0 is invalid" in caplog.text


def test_check_filepaths_cwd():
    class Test(PathSchema):
        cwd = "cwd"

        def __init__(self):
            super().__init__()

            schema = EditableSchema(self)
            schema.insert("dir", Parameter("dir"))

    test = Test()
    assert test.set("dir", "test")

    os.makedirs("cwd/test", exist_ok=True)

    assert test.check_filepaths() is True


def test_check_filepaths_collection_dir():
    class Test(PathSchema):
        calls = 0

        def collection_dir(self):
            self.calls += 1
            return os.path.abspath("collect")

        def __init__(self):
            super().__init__()

            schema = EditableSchema(self)
            schema.insert("dir", Parameter("dir"))

    test = Test()
    assert test.set("dir", "test")

    os.makedirs("collect/test_3a52ce780950d4d969792a2559cd519d7ee8c727", exist_ok=True)

    assert test.check_filepaths() is True
    assert test.calls == 1
