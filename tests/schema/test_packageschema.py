import pytest

from siliconcompiler.schema import PackageSchema
from siliconcompiler.schema import EditableSchema, Parameter


def test_invalid_package():
    with pytest.raises(ValueError, match="package must be a string"):
        PackageSchema(package=[])


def test_no_package_set():
    schema = PackageSchema()
    edit = EditableSchema(schema)
    edit.insert("str0", Parameter("str"))
    edit.insert("file0", Parameter("file"))

    assert schema.set("file0", "./test")
    assert schema.get("file0", field="package") is None

    assert schema.set("file0", "./test", package="thispackage")
    assert schema.get("file0", field="package") == "thispackage"


def test_with_package_set():
    schema = PackageSchema(package="thispackage")
    edit = EditableSchema(schema)
    edit.insert("str0", Parameter("str"))
    edit.insert("file0", Parameter("file"))

    assert schema.set("file0", "./test")
    assert schema.get("file0", field="package") == "thispackage"


def test_with_package_set_different():
    schema = PackageSchema(package="thispackage")
    edit = EditableSchema(schema)
    edit.insert("str0", Parameter("str"))
    edit.insert("file0", Parameter("file"))

    assert schema.set("file0", "./test", package="otherpackage")
    assert schema.get("file0", field="package") == "otherpackage"


def test_no_package_add():
    schema = PackageSchema()
    edit = EditableSchema(schema)
    edit.insert("str0", Parameter("str"))
    edit.insert("file0", Parameter("[file]"))

    assert schema.add("file0", "./test")
    assert schema.get("file0", field="package") == [None]
    assert schema.add("file0", "./test", package="thispackage")
    assert schema.get("file0", field="package") == [None, "thispackage"]


def test_with_package_add():
    schema = PackageSchema(package="thispackage")
    edit = EditableSchema(schema)
    edit.insert("str0", Parameter("str"))
    edit.insert("file0", Parameter("[file]"))

    assert schema.add("file0", "./test")
    assert schema.get("file0", field="package") == ["thispackage"]


def test_with_package_add_different():
    schema = PackageSchema(package="thispackage")
    edit = EditableSchema(schema)
    edit.insert("str0", Parameter("str"))
    edit.insert("file0", Parameter("[file]"))

    assert schema.add("file0", "./test", package="otherpackage")
    assert schema.get("file0", field="package") == ["otherpackage"]


def test_no_package_multiple_add():
    schema = PackageSchema()
    edit = EditableSchema(schema)
    edit.insert("str0", Parameter("str"))
    edit.insert("file0", Parameter("[file]"))

    assert schema.add("file0", ["./test", "./there"])
    assert schema.get("file0", field="package") == [None, None]


def test_with_package_multiple_add():
    schema = PackageSchema(package="thispackage")
    edit = EditableSchema(schema)
    edit.insert("str0", Parameter("str"))
    edit.insert("file0", Parameter("[file]"))

    assert schema.add("file0", ["./test", "./there"])
    assert schema.get("file0", field="package") == ["thispackage", "thispackage"]


def test_with_package_multiple_add_different():
    schema = PackageSchema(package="thispackage")
    edit = EditableSchema(schema)
    edit.insert("str0", Parameter("str"))
    edit.insert("file0", Parameter("[file]"))

    assert schema.add("file0", ["./test", "./there"], package="otherpackage")
    assert schema.get("file0", field="package") == ["otherpackage", "otherpackage"]


def test_with_package_multiple_add_mixed():
    schema = PackageSchema(package="thispackage")
    edit = EditableSchema(schema)
    edit.insert("str0", Parameter("str"))
    edit.insert("file0", Parameter("[file]"))

    assert schema.add("file0", ["./test", "./there"], package=["otherpackage0", "otherpackage1"])
    assert schema.get("file0", field="package") == ["otherpackage0", "otherpackage1"]


def test_with_package_multiple_add_mixed_invalid():
    schema = PackageSchema(package="thispackage")
    edit = EditableSchema(schema)
    edit.insert("str0", Parameter("str"))
    edit.insert("file0", Parameter("[file]"))

    with pytest.raises(ValueError, match="unable to determine package mapping"):
        schema.add("file0", ["./test", "./there", "./this"],
                   package=["otherpackage0", "otherpackage1"])
