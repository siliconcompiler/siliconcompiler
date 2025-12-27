import pytest

from siliconcompiler import Design
from siliconcompiler.schema import PerNode, Scope

from siliconcompiler.constraints import TimingModeSchema


def test_timing_mode_keys():
    assert TimingModeSchema().allkeys() == set([
        ('sdcfileset',)
    ])


@pytest.mark.parametrize("key", TimingModeSchema().allkeys())
def test_timing_mode_key_params(key):
    param = TimingModeSchema().get(*key, field=None)
    assert param.get(field="pernode") == PerNode.OPTIONAL
    assert param.get(field="scope") == Scope.GLOBAL


def test_timing_mode_sdcfileset_invalid_type_design():
    with pytest.raises(TypeError, match=r"^design must be a design object or string$"):
        TimingModeSchema().add_sdcfileset(1.0, "fileset")


def test_timing_mode_sdcfileset_invalid_type_fileset():
    with pytest.raises(TypeError, match=r"^fileset must be a string$"):
        TimingModeSchema().add_sdcfileset("test", 1.0)


def test_timing_mode_sdcfileset_design_obj():
    scene = TimingModeSchema()

    design = Design("test")
    assert scene.add_sdcfileset(design, "rtl")
    assert scene.get("sdcfileset") == [("test", "rtl")]
    assert scene.get_sdcfileset() == [("test", "rtl")]


def test_timing_mode_sdcfileset_design_str():
    scene = TimingModeSchema()

    assert scene.add_sdcfileset("test", "rtl")
    assert scene.get("sdcfileset") == [("test", "rtl")]
    assert scene.get_sdcfileset() == [("test", "rtl")]


def test_timing_mode_sdcfileset_design_step_index():
    scene = TimingModeSchema()

    assert scene.add_sdcfileset("test", "rtl")
    assert scene.add_sdcfileset("test1", "rtl1", step="step0", index="1")
    assert scene.get("sdcfileset") == [("test", "rtl")]
    assert scene.get_sdcfileset() == [("test", "rtl")]
    assert scene.get("sdcfileset", step="step0", index="1") == [("test1", "rtl1")]
    assert scene.get_sdcfileset(step="step0", index="1") == [("test1", "rtl1")]


def test_timing_mode_sdcfileset_design_clobber():
    scene = TimingModeSchema()

    assert scene.add_sdcfileset("test", "rtl")
    assert scene.add_sdcfileset("test1", "rtl1", step="step0", index="1")
    assert scene.get_sdcfileset() == [("test", "rtl")]
    assert scene.get_sdcfileset(step="step0", index="1") == [("test1", "rtl1")]
    assert scene.add_sdcfileset("test1", "rtl", step="step0", index="1", clobber=True)
    assert scene.get_sdcfileset() == [("test", "rtl")]
    assert scene.get_sdcfileset(step="step0", index="1") == [("test1", "rtl")]
