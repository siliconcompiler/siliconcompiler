from siliconcompiler.packageschema import PackageSchema


def test_register():
    schema = PackageSchema()
    assert schema.getkeys("source") == tuple()
    assert schema.register("testpackage", "pathtosource") is True
    assert schema.get("source", "testpackage", "path") == "pathtosource"
    assert schema.get("source", "testpackage", "ref") is None


def test_register_ref():
    schema = PackageSchema()
    assert schema.getkeys("source") == tuple()
    assert schema.register("testpackage", "pathtosource", ref="123456") is True
    assert schema.get("source", "testpackage", "path") == "pathtosource"
    assert schema.get("source", "testpackage", "ref") == "123456"


def test_register_ref_no_clobber():
    schema = PackageSchema()
    assert schema.getkeys("source") == tuple()
    assert schema.register("testpackage", "pathtosource", ref="123456") is True
    assert schema.get("source", "testpackage", "path") == "pathtosource"
    assert schema.get("source", "testpackage", "ref") == "123456"
    assert schema.register("testpackage", "pathtosource", ref="1234567", clobber=False) is False
    assert schema.get("source", "testpackage", "ref") == "123456"


def test_register_ref_with_clobber():
    schema = PackageSchema()
    assert schema.getkeys("source") == tuple()
    assert schema.register("testpackage", "pathtosource", ref="123456") is True
    assert schema.get("source", "testpackage", "path") == "pathtosource"
    assert schema.get("source", "testpackage", "ref") == "123456"
    assert schema.register("testpackage", "pathtosource", ref="1234567", clobber=True) is True
    assert schema.get("source", "testpackage", "ref") == "1234567"
