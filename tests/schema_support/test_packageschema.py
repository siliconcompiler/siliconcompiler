import os

import os.path

from pathlib import Path

from siliconcompiler.schema_support.packageschema import PackageSchema


def test_keys():
    assert PackageSchema().allkeys() == set([
        ('dataroot', 'default', 'path'),
        ('dataroot', 'default', 'tag'),
        ('package', 'author', 'default', 'email'),
        ('package', 'author', 'default', 'name'),
        ('package', 'author', 'default', 'organization'),
        ('package', 'description'),
        ('package', 'doc', 'datasheet'),
        ('package', 'doc', 'quickstart'),
        ('package', 'doc', 'reference'),
        ('package', 'doc', 'releasenotes'),
        ('package', 'doc', 'signoff'),
        ('package', 'doc', 'testplan'),
        ('package', 'doc', 'tutorial'),
        ('package', 'doc', 'userguide'),
        ('package', 'license'),
        ('package', 'licensefile'),
        ('package', 'vendor'),
        ('package', 'version'),
    ])


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


def test_vendor():
    schema = PackageSchema()
    assert schema.set_vendor("acme")
    assert schema.get("package", "vendor") == "acme"
    assert schema.get_vendor() == "acme"


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
