from siliconcompiler.pdk import PDKSchema


def test_set_add():
    schema = PDKSchema("testpdk")
    assert schema.name == "testpdk"
