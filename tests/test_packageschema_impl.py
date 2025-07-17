import os

import os.path

from pathlib import Path

from siliconcompiler.packageschema import PackageSchema
from siliconcompiler.packageschema import PackageSchemaTmp


def test_register():
    schema = PackageSchemaTmp()
    assert schema.getkeys("source") == tuple()
    assert schema.register("testpackage", "pathtosource") is True
    assert schema.get("source", "testpackage", "path") == "pathtosource"
    assert schema.get("source", "testpackage", "ref") is None


def test_register_ref():
    schema = PackageSchemaTmp()
    assert schema.getkeys("source") == tuple()
    assert schema.register("testpackage", "pathtosource", ref="123456") is True
    assert schema.get("source", "testpackage", "path") == "pathtosource"
    assert schema.get("source", "testpackage", "ref") == "123456"


def test_register_ref_no_clobber():
    schema = PackageSchemaTmp()
    assert schema.getkeys("source") == tuple()
    assert schema.register("testpackage", "pathtosource", ref="123456") is True
    assert schema.get("source", "testpackage", "path") == "pathtosource"
    assert schema.get("source", "testpackage", "ref") == "123456"
    assert schema.register("testpackage", "pathtosource", ref="1234567", clobber=False) is False
    assert schema.get("source", "testpackage", "ref") == "123456"


def test_register_ref_with_clobber():
    schema = PackageSchemaTmp()
    assert schema.getkeys("source") == tuple()
    assert schema.register("testpackage", "pathtosource", ref="123456") is True
    assert schema.get("source", "testpackage", "path") == "pathtosource"
    assert schema.get("source", "testpackage", "ref") == "123456"
    assert schema.register("testpackage", "pathtosource", ref="1234567", clobber=True) is True
    assert schema.get("source", "testpackage", "ref") == "1234567"


def test_register_ref_file():
    schema = PackageSchemaTmp()
    assert schema.getkeys("source") == tuple()
    with open("test.txt", "w") as f:
        f.write("test")

    assert schema.register("testpackage", "test.txt") is True
    assert schema.get("source", "testpackage", "path") == os.path.abspath(".")
    assert schema.get("source", "testpackage", "ref") is None


def test_register_ref_dir():
    schema = PackageSchemaTmp()
    assert schema.getkeys("source") == tuple()

    assert schema.register("testpackage", ".") is True
    assert schema.get("source", "testpackage", "path") == os.path.abspath(".")
    assert schema.get("source", "testpackage", "ref") is None


def test_get_resolvers_empty():
    schema = PackageSchemaTmp()
    assert schema.get_resolvers() == {}


def test_description():
    schema = PackageSchema()
    assert schema.set_description("this is the description")
    assert schema.get("package", "description") == "this is the description"
    assert schema.get_description() == "this is the description"


def test_version():
    schema = PackageSchema()
    assert schema.set_version("1.0")
    assert schema.get("package", "version") == "1.0"
    assert schema.get_version() == "1.0"


def test_author():
    schema = PackageSchema()
    assert len(schema.add_author("person0",
                                 name="Bob",
                                 email="bob@org.com",
                                 organization="Bob Inc.")) == 3
    assert schema.get("package", "author", "person0", "name") == "Bob"
    assert schema.get("package", "author", "person0", "email") == "bob@org.com"
    assert schema.get("package", "author", "person0", "organization") == "Bob Inc."

    assert schema.get_author("person0") == {
        "email": "bob@org.com",
        "name": "Bob",
        "organization": "Bob Inc."
    }


def test_author_overwrite():
    schema = PackageSchema()
    assert len(schema.add_author("person0",
                                 name="Bob",
                                 email="bob@org.com",
                                 organization="Bob Inc.")) == 3
    assert len(schema.add_author("person0", name="Bob0")) == 1
    assert schema.get("package", "author", "person0", "name") == "Bob0"
    assert schema.get("package", "author", "person0", "email") == "bob@org.com"
    assert schema.get("package", "author", "person0", "organization") == "Bob Inc."


def test_author_multiple():
    schema = PackageSchema()
    assert len(schema.add_author("person0",
                                 name="Bob",
                                 email="bob@org.com",
                                 organization="AMCE Inc.")) == 3
    assert len(schema.add_author("person1",
                                 name="Alice",
                                 email="alice@org.com",
                                 organization="AMCE Inc.")) == 3

    assert schema.get_author() == [
        {
            "email": "bob@org.com",
            "name": "Bob",
            "organization": "AMCE Inc."
        },
        {
            "email": "alice@org.com",
            "name": "Alice",
            "organization": "AMCE Inc."
        }
    ]


def test_license():
    schema = PackageSchema()
    assert schema.add_license("fake0")
    assert schema.add_license("fake1")
    assert schema.get_license() == ["fake0", "fake1"]


def test_licensefile():
    schema = PackageSchema()
    Path("lic").touch()

    assert schema.add_licensefile("./lic")
    assert schema.get_licensefile() == [os.path.abspath("lic")]


def test_licensefile_with_dataroot():
    schema = PackageSchema()

    os.makedirs("lics", exist_ok=True)
    Path("lics/lic").touch()

    schema.set_dataroot("testdata", os.path.abspath("lics"))

    with schema.active_dataroot("testdata"):
        assert schema.add_licensefile("./lic")
    assert schema.get_licensefile() == [os.path.abspath("lics/lic")]


def test_add_doc():
    schema = PackageSchema()

    Path("doc").touch()

    assert schema.add_doc("userguide", "doc")
    assert schema.get("package", "doc", "userguide") == ["doc"]
    assert schema.get_doc("userguide") == [os.path.abspath("doc")]


def test_add_doc_with_dataroot():
    schema = PackageSchema()

    os.makedirs("docs", exist_ok=True)
    Path("docs/quick").touch()

    schema.set_dataroot("testdata", os.path.abspath("docs"))

    with schema.active_dataroot("testdata"):
        assert schema.add_doc("quickstart", "quick")
    assert schema.get("package", "doc", "quickstart") == ["quick"]
    assert schema.get_doc("quickstart") == [os.path.abspath("docs/quick")]


def test_get_doc_all():
    schema = PackageSchema()

    os.makedirs("docs", exist_ok=True)
    Path("docs/quick").touch()
    Path("user").touch()

    assert schema.add_doc("userguide", "user")
    schema.set_dataroot("testdata", os.path.abspath("docs"))

    with schema.active_dataroot("testdata"):
        assert schema.add_doc("quickstart", "quick")

    assert schema.get_doc() == {
        "quickstart": [os.path.abspath("docs/quick")],
        "userguide": [os.path.abspath("user")],
    }
