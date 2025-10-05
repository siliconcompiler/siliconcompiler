import pytest

from siliconcompiler import Design
from siliconcompiler.schema import PerNode, Scope

from siliconcompiler.constraints import ASICTimingScenarioSchema, ASICTimingConstraintSchema


def test_timing_scanario_keys():
    assert ASICTimingScenarioSchema().allkeys() == set([
        ('check',),
        ('libcorner',),
        ('mode',),
        ('opcond',),
        ('pexcorner',),
        ('sdcfileset',),
        ('temperature',),
        ('voltage', 'default',),
    ])


@pytest.mark.parametrize("key", ASICTimingScenarioSchema().allkeys())
def test_timing_scanario_key_params(key):
    param = ASICTimingScenarioSchema().get(*key, field=None)
    assert param.get(field="pernode") == PerNode.OPTIONAL
    assert param.get(field="scope") == Scope.GLOBAL


def test_timing_scanario_pin_voltage():
    scene = ASICTimingScenarioSchema()
    assert scene.set_pin_voltage("VDD", 1.8)
    assert scene.set_pin_voltage("VDD", 2.5, step="step0", index="1")
    assert scene.get("voltage", "VDD") == 1.8
    assert scene.get_pin_voltage("VDD") == 1.8
    assert scene.get("voltage", "VDD", step="step0", index="1") == 2.5
    assert scene.get_pin_voltage("VDD", step="step0", index="1") == 2.5


def test_timing_scanario_pin_voltage_missing():
    scene = ASICTimingScenarioSchema()
    with pytest.raises(LookupError, match="^VDD does not have voltage$"):
        scene.get_pin_voltage("VDD")


def test_timing_scanario_libcorner():
    scene = ASICTimingScenarioSchema()
    assert scene.add_libcorner("slow0")
    assert scene.add_libcorner("slow1")
    assert scene.add_libcorner("slow2", step="step0", index="1")
    assert scene.get("libcorner") == ["slow0", "slow1"]
    assert scene.get_libcorner() == ["slow0", "slow1"]
    assert scene.get("libcorner", step="step0", index="1") == ["slow2"]
    assert scene.get_libcorner(step="step0", index="1") == ["slow2"]


def test_timing_scanario_libcorner_clobber():
    scene = ASICTimingScenarioSchema()
    assert scene.add_libcorner("slow0")
    assert scene.get_libcorner() == ["slow0"]
    assert scene.add_libcorner("slow1", clobber=True)
    assert scene.get_libcorner() == ["slow1"]


def test_timing_scanario_libcorner_clobber_step_index():
    scene = ASICTimingScenarioSchema()
    assert scene.add_libcorner("slow0")
    assert scene.add_libcorner("slow1", step="step0", index="1")
    assert scene.get_libcorner() == ["slow0"]
    assert scene.get_libcorner(step="step0", index="1") == ["slow1"]
    assert scene.add_libcorner("slow2", step="step0", index="1", clobber=True)
    assert scene.get_libcorner() == ["slow0"]
    assert scene.get_libcorner(step="step0", index="1") == ["slow2"]


def test_timing_scanario_pexcorner():
    scene = ASICTimingScenarioSchema()
    assert scene.set_pexcorner("ff")
    assert scene.set_pexcorner("ss", step="step0", index="1")
    assert scene.get("pexcorner") == "ff"
    assert scene.get_pexcorner() == "ff"
    assert scene.get("pexcorner", step="step0", index="1") == "ss"
    assert scene.get_pexcorner(step="step0", index="1") == "ss"


def test_timing_scanario_mode():
    scene = ASICTimingScenarioSchema()
    assert scene.set_mode("run")
    assert scene.set_mode("test", step="step0", index="1")
    assert scene.get("mode") == "run"
    assert scene.get_mode() == "run"
    assert scene.get("mode", step="step0", index="1") == "test"
    assert scene.get_mode(step="step0", index="1") == "test"


def test_timing_scanario_opcond():
    scene = ASICTimingScenarioSchema()
    assert scene.set_opcond("op0")
    assert scene.set_opcond("op1", step="step0", index="1")
    assert scene.get("opcond") == "op0"
    assert scene.get_opcond() == "op0"
    assert scene.get("opcond", step="step0", index="1") == "op1"
    assert scene.get_opcond(step="step0", index="1") == "op1"


def test_timing_scanario_temperature():
    scene = ASICTimingScenarioSchema()
    assert scene.set_temperature(125.0)
    assert scene.set_temperature(-40, step="step0", index="1")
    assert scene.get("temperature") == 125.0
    assert scene.get_temperature() == 125.0
    assert scene.get("temperature", step="step0", index="1") == -40.0
    assert scene.get_temperature(step="step0", index="1") == -40.0


def test_timing_scanario_check():
    scene = ASICTimingScenarioSchema()
    assert scene.add_check("setup")
    assert scene.add_check("hold", step="step0", index="1")
    assert scene.get("check") == ["setup"]
    assert scene.get_check() == ["setup"]
    assert scene.get("check", step="step0", index="1") == ["hold"]
    assert scene.get_check(step="step0", index="1") == ["hold"]


def test_timing_scanario_check_clobber():
    scene = ASICTimingScenarioSchema()
    assert scene.add_check("setup")
    assert scene.get_check() == ["setup"]
    assert scene.add_check("hold", clobber=True)
    assert scene.get_check() == ["hold"]


def test_timing_scanario_check_clobber_step_index():
    scene = ASICTimingScenarioSchema()
    assert scene.add_check("setup")
    assert scene.add_check("hold", step="step0", index="1")
    assert scene.get_check() == ["setup"]
    assert scene.get_check(step="step0", index="1") == ["hold"]
    assert scene.add_check("power", step="step0", index="1", clobber=True)
    assert scene.get_check() == ["setup"]
    assert scene.get_check(step="step0", index="1") == ["power"]


def test_timing_scanario_sdcfileset_invalid_type_design():
    with pytest.raises(TypeError, match="^design must be a design object or string$"):
        ASICTimingScenarioSchema().add_sdcfileset(1.0, "fileset")


def test_timing_scanario_sdcfileset_invalid_type_fileset():
    with pytest.raises(TypeError, match="^fileset must be a string$"):
        ASICTimingScenarioSchema().add_sdcfileset("test", 1.0)


def test_timing_scanario_sdcfileset_design_obj():
    scene = ASICTimingScenarioSchema()

    design = Design("test")
    assert scene.add_sdcfileset(design, "rtl")
    assert scene.get("sdcfileset") == [("test", "rtl")]
    assert scene.get_sdcfileset() == [("test", "rtl")]


def test_timing_scanario_sdcfileset_design_str():
    scene = ASICTimingScenarioSchema()

    assert scene.add_sdcfileset("test", "rtl")
    assert scene.get("sdcfileset") == [("test", "rtl")]
    assert scene.get_sdcfileset() == [("test", "rtl")]


def test_timing_scanario_sdcfileset_design_step_index():
    scene = ASICTimingScenarioSchema()

    assert scene.add_sdcfileset("test", "rtl")
    assert scene.add_sdcfileset("test1", "rtl1", step="step0", index="1")
    assert scene.get("sdcfileset") == [("test", "rtl")]
    assert scene.get_sdcfileset() == [("test", "rtl")]
    assert scene.get("sdcfileset", step="step0", index="1") == [("test1", "rtl1")]
    assert scene.get_sdcfileset(step="step0", index="1") == [("test1", "rtl1")]


def test_timing_scanario_sdcfileset_design_clobber():
    scene = ASICTimingScenarioSchema()

    assert scene.add_sdcfileset("test", "rtl")
    assert scene.add_sdcfileset("test1", "rtl1", step="step0", index="1")
    assert scene.get_sdcfileset() == [("test", "rtl")]
    assert scene.get_sdcfileset(step="step0", index="1") == [("test1", "rtl1")]
    assert scene.add_sdcfileset("test1", "rtl", step="step0", index="1", clobber=True)
    assert scene.get_sdcfileset() == [("test", "rtl")]
    assert scene.get_sdcfileset(step="step0", index="1") == [("test1", "rtl")]


def test_timing_constraint_keys():
    assert ASICTimingConstraintSchema().allkeys() == set([
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
    assert ASICTimingConstraintSchema().get_scenario() == {}


def test_timing_constraint_get_scenarios_missing():
    with pytest.raises(LookupError, match="^notfound is not defined$"):
        ASICTimingConstraintSchema().get_scenario("notfound")


def test_timing_constraint_add_scenario_invalid_type():
    with pytest.raises(TypeError, match="^scenario must be a timing scenario object$"):
        ASICTimingConstraintSchema().add_scenario(ASICTimingConstraintSchema())


def test_timing_constraint_add_scenario_unnamed():
    with pytest.raises(ValueError, match="^scenario must have a name$"):
        ASICTimingConstraintSchema().add_scenario(ASICTimingScenarioSchema())


def test_timing_constraint_add_scenario():
    scene = ASICTimingScenarioSchema("slow")
    schema = ASICTimingConstraintSchema()

    schema.add_scenario(scene)
    assert schema.getkeys() == ("slow",)
    assert schema.get_scenario("slow") is scene


def test_timing_constraint_get_scenario():
    scene_s = ASICTimingScenarioSchema("slow")
    scene_f = ASICTimingScenarioSchema("fast")
    schema = ASICTimingConstraintSchema()

    schema.add_scenario(scene_s)
    schema.add_scenario(scene_f)
    assert schema.getkeys() == ("fast", "slow")
    assert schema.get_scenario() == {
        "slow": scene_s,
        "fast": scene_f
    }


def test_timing_constraint_make_scenario_illegal():
    with pytest.raises(ValueError, match="^scenario name is required$"):
        ASICTimingConstraintSchema().make_scenario(None)


def test_timing_constraint_make_scenario_exists():
    schema = ASICTimingConstraintSchema()

    schema.add_scenario(ASICTimingScenarioSchema("slow"))
    with pytest.raises(LookupError, match="^slow scenario already exists$"):
        schema.make_scenario("slow")


def test_timing_constraint_make_scenario():
    schema = ASICTimingConstraintSchema()

    constraint = schema.make_scenario("slow")
    assert isinstance(constraint, ASICTimingScenarioSchema)
    assert constraint.name == "slow"
    assert schema.get("slow", field="schema") is constraint


def test_timing_constraint_remove_scenario_illegal():
    with pytest.raises(ValueError, match="^scenario name is required$"):
        ASICTimingConstraintSchema().remove_scenario(None)


def test_timing_constraint_remove_scenario_not_found():
    assert ASICTimingConstraintSchema().remove_scenario("slow") is False


def test_timing_constraint_remove_scenario():
    schema = ASICTimingConstraintSchema()

    schema.make_scenario("slow")
    assert schema.getkeys() == ("slow",)
    assert schema.remove_scenario("slow") is True
    assert schema.getkeys() == tuple()
