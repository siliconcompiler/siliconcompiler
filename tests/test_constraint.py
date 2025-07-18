import pytest

from siliconcompiler import DesignSchema
from siliconcompiler.schema import PerNode, Scope

from siliconcompiler.constraint import TimingScenarioSchema, TimingConstraintSchema


def test_timing_scanario_keys():
    assert TimingScenarioSchema().allkeys() == set([
        ('check',),
        ('libcorner',),
        ('mode',),
        ('opcond',),
        ('pexcorner',),
        ('sdcfileset',),
        ('temperature',),
        ('voltage', 'default',),
    ])


@pytest.mark.parametrize("key", TimingScenarioSchema().allkeys())
def test_timing_scanario_key_params(key):
    param = TimingScenarioSchema().get(*key, field=None)
    assert param.get(field="pernode") == PerNode.OPTIONAL
    assert param.get(field="scope") == Scope.GLOBAL


def test_timing_scanario_pin_voltage():
    scene = TimingScenarioSchema()
    assert scene.set_pin_voltage("VDD", 1.8)
    assert scene.set_pin_voltage("VDD", 2.5, step="step0", index="1")
    assert scene.get("voltage", "VDD") == 1.8
    assert scene.get_pin_voltage("VDD") == 1.8
    assert scene.get("voltage", "VDD", step="step0", index="1") == 2.5
    assert scene.get_pin_voltage("VDD", step="step0", index="1") == 2.5


def test_timing_scanario_pin_voltage_missing():
    scene = TimingScenarioSchema()
    with pytest.raises(LookupError, match="VDD does not have voltage"):
        scene.get_pin_voltage("VDD")


def test_timing_scanario_libcorner():
    scene = TimingScenarioSchema()
    assert scene.add_libcorner("slow0")
    assert scene.add_libcorner("slow1")
    assert scene.add_libcorner("slow2", step="step0", index="1")
    assert scene.get("libcorner") == set(["slow0", "slow1"])
    assert scene.get_libcorner() == set(["slow0", "slow1"])
    assert scene.get("libcorner", step="step0", index="1") == set(["slow2"])
    assert scene.get_libcorner(step="step0", index="1") == set(["slow2"])


def test_timing_scanario_libcorner_clobber():
    scene = TimingScenarioSchema()
    assert scene.add_libcorner("slow0")
    assert scene.get_libcorner() == set(["slow0"])
    assert scene.add_libcorner("slow1", clobber=True)
    assert scene.get_libcorner() == set(["slow1"])


def test_timing_scanario_libcorner_clobber_step_index():
    scene = TimingScenarioSchema()
    assert scene.add_libcorner("slow0")
    assert scene.add_libcorner("slow1", step="step0", index="1")
    assert scene.get_libcorner() == set(["slow0"])
    assert scene.get_libcorner(step="step0", index="1") == set(["slow1"])
    assert scene.add_libcorner("slow2", step="step0", index="1", clobber=True)
    assert scene.get_libcorner() == set(["slow0"])
    assert scene.get_libcorner(step="step0", index="1") == set(["slow2"])


def test_timing_scanario_pexcorner():
    scene = TimingScenarioSchema()
    assert scene.set_pexcorner("ff")
    assert scene.set_pexcorner("ss", step="step0", index="1")
    assert scene.get("pexcorner") == "ff"
    assert scene.get_pexcorner() == "ff"
    assert scene.get("pexcorner", step="step0", index="1") == "ss"
    assert scene.get_pexcorner(step="step0", index="1") == "ss"


def test_timing_scanario_mode():
    scene = TimingScenarioSchema()
    assert scene.set_mode("run")
    assert scene.set_mode("test", step="step0", index="1")
    assert scene.get("mode") == "run"
    assert scene.get_mode() == "run"
    assert scene.get("mode", step="step0", index="1") == "test"
    assert scene.get_mode(step="step0", index="1") == "test"


def test_timing_scanario_opcond():
    scene = TimingScenarioSchema()
    assert scene.set_opcond("op0")
    assert scene.set_opcond("op1", step="step0", index="1")
    assert scene.get("opcond") == "op0"
    assert scene.get_opcond() == "op0"
    assert scene.get("opcond", step="step0", index="1") == "op1"
    assert scene.get_opcond(step="step0", index="1") == "op1"


def test_timing_scanario_temperature():
    scene = TimingScenarioSchema()
    assert scene.set_temperature(125.0)
    assert scene.set_temperature(-40, step="step0", index="1")
    assert scene.get("temperature") == 125.0
    assert scene.get_temperature() == 125.0
    assert scene.get("temperature", step="step0", index="1") == -40.0
    assert scene.get_temperature(step="step0", index="1") == -40.0


def test_timing_scanario_check():
    scene = TimingScenarioSchema()
    assert scene.add_check("setup")
    assert scene.add_check("hold", step="step0", index="1")
    assert scene.get("check") == set(["setup"])
    assert scene.get_check() == set(["setup"])
    assert scene.get("check", step="step0", index="1") == set(["hold"])
    assert scene.get_check(step="step0", index="1") == set(["hold"])


def test_timing_scanario_check_clobber():
    scene = TimingScenarioSchema()
    assert scene.add_check("setup")
    assert scene.get_check() == set(["setup"])
    assert scene.add_check("hold", clobber=True)
    assert scene.get_check() == set(["hold"])


def test_timing_scanario_check_clobber_step_index():
    scene = TimingScenarioSchema()
    assert scene.add_check("setup")
    assert scene.add_check("hold", step="step0", index="1")
    assert scene.get_check() == set(["setup"])
    assert scene.get_check(step="step0", index="1") == set(["hold"])
    assert scene.add_check("power", step="step0", index="1", clobber=True)
    assert scene.get_check() == set(["setup"])
    assert scene.get_check(step="step0", index="1") == set(["power"])


def test_timing_scanario_sdcfileset_invalid_type_design():
    with pytest.raises(TypeError, match="design must be a design object or string"):
        TimingScenarioSchema().add_sdcfileset(1.0, "fileset")


def test_timing_scanario_sdcfileset_invalid_type_fileset():
    with pytest.raises(TypeError, match="fileset must be a string"):
        TimingScenarioSchema().add_sdcfileset("test", 1.0)


def test_timing_scanario_sdcfileset_design_obj():
    scene = TimingScenarioSchema()

    design = DesignSchema("test")
    assert scene.add_sdcfileset(design, "rtl")
    assert scene.get("sdcfileset") == [("test", "rtl")]
    assert scene.get_sdcfileset() == [("test", "rtl")]


def test_timing_scanario_sdcfileset_design_str():
    scene = TimingScenarioSchema()

    assert scene.add_sdcfileset("test", "rtl")
    assert scene.get("sdcfileset") == [("test", "rtl")]
    assert scene.get_sdcfileset() == [("test", "rtl")]


def test_timing_scanario_sdcfileset_design_step_index():
    scene = TimingScenarioSchema()

    assert scene.add_sdcfileset("test", "rtl")
    assert scene.add_sdcfileset("test1", "rtl1", step="step0", index="1")
    assert scene.get("sdcfileset") == [("test", "rtl")]
    assert scene.get_sdcfileset() == [("test", "rtl")]
    assert scene.get("sdcfileset", step="step0", index="1") == [("test1", "rtl1")]
    assert scene.get_sdcfileset(step="step0", index="1") == [("test1", "rtl1")]


def test_timing_scanario_sdcfileset_design_clobber():
    scene = TimingScenarioSchema()

    assert scene.add_sdcfileset("test", "rtl")
    assert scene.add_sdcfileset("test1", "rtl1", step="step0", index="1")
    assert scene.get_sdcfileset() == [("test", "rtl")]
    assert scene.get_sdcfileset(step="step0", index="1") == [("test1", "rtl1")]
    assert scene.add_sdcfileset("test1", "rtl", step="step0", index="1", clobber=True)
    assert scene.get_sdcfileset() == [("test", "rtl")]
    assert scene.get_sdcfileset(step="step0", index="1") == [("test1", "rtl")]


def test_timing_constraint_keys():
    assert TimingConstraintSchema().allkeys() == set([
        ('default', 'check',),
        ('default', 'libcorner',),
        ('default', 'mode',),
        ('default', 'opcond',),
        ('default', 'pexcorner',),
        ('default', 'sdcfileset',),
        ('default', 'temperature',),
        ('default', 'voltage', 'default',),
    ])


def test_timing_constraint_get_scenarios_empty():
    assert TimingConstraintSchema().get_scenario() == {}


def test_timing_constraint_get_scenarios_missing():
    with pytest.raises(LookupError, match="notfound is not defined"):
        TimingConstraintSchema().get_scenario("notfound")


def test_timing_constraint_add_scenario_invalid_type():
    with pytest.raises(TypeError, match="scenario must be a timing scenario object"):
        TimingConstraintSchema().add_scenario(TimingConstraintSchema())


def test_timing_constraint_add_scenario_unnamed():
    with pytest.raises(ValueError, match="scenario must have a name"):
        TimingConstraintSchema().add_scenario(TimingScenarioSchema())


def test_timing_constraint_add_scenario():
    scene = TimingScenarioSchema("slow")
    schema = TimingConstraintSchema()

    schema.add_scenario(scene)
    assert schema.getkeys() == ("slow",)
    assert schema.get_scenario("slow") is scene


def test_timing_constraint_get_scenario():
    scene_s = TimingScenarioSchema("slow")
    scene_f = TimingScenarioSchema("fast")
    schema = TimingConstraintSchema()

    schema.add_scenario(scene_s)
    schema.add_scenario(scene_f)
    assert schema.getkeys() == ("fast", "slow")
    assert schema.get_scenario() == {
        "slow": scene_s,
        "fast": scene_f
    }
