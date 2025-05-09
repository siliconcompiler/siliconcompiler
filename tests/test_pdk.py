from siliconcompiler.pdk import PDKSchema


def test_set_add():
    schema = PDKSchema()

    assert schema.set("doc", "test", "./this.txt", package="thispackage")
    assert schema.get("doc", "test") == ["this.txt"]
    assert schema.get("doc", "test", field='package') == ["thispackage"]
    assert schema.add("doc", "test", "./that.txt", package="thatpackage")
    assert schema.get("doc", "test") == ["this.txt", "that.txt"]
    assert schema.get("doc", "test", field='package') == ["thispackage", "thatpackage"]
