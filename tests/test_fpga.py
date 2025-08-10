from siliconcompiler import FPGASchema


def test_set_add():
    schema = FPGASchema("testfpga")
    assert schema.name == "testfpga"


def test_fpga_keys():
    assert FPGASchema().allkeys("fpga") == {
        ('lutsize',),
        ('partname',)
    }


def test_keys():
    assert FPGASchema().getkeys() == (
        'dataroot',
        'fileset',
        'fpga',
        'package'
    )


def test_getdict_type():
    assert FPGASchema._getdict_type() == "FPGASchema"


def test_set_partname():
    schema = FPGASchema()
    assert schema.get("fpga", "partname") is None
    schema.set_partname("fpga123")
    assert schema.get("fpga", "partname") == "fpga123"


def test_set_lutsize():
    schema = FPGASchema()
    assert schema.get("fpga", "lutsize") is None
    schema.set_lutsize(6)
    assert schema.get("fpga", "lutsize") == 6
