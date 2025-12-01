import pytest

from siliconcompiler import Design
from siliconcompiler.schema import PerNode, Scope

from siliconcompiler.constraints import ASICTimingScenarioSchema, ASICTimingConstraintSchema, \
    TimingModeSchema


def test_timing_scenario_keys():
    assert ASICTimingScenarioSchema().allkeys() == set([
        ('check',),
        ('libcorner',),
        ('mode',),
        ('opcond',),
        ('pexcorner',),
        ('temperature',),
        ('voltage', 'default',),
    ])


@pytest.mark.parametrize("key", ASICTimingScenarioSchema().allkeys())
def test_timing_scenario_key_params(key):
    param = ASICTimingScenarioSchema().get(*key, field=None)
    assert param.get(field="pernode") == PerNode.OPTIONAL
    assert param.get(field="scope") == Scope.GLOBAL


def test_timing_scenario_pin_voltage():
    scene = ASICTimingScenarioSchema()
    assert scene.set_pin_voltage("VDD", 1.8)
    assert scene.set_pin_voltage("VDD", 2.5, step="step0", index="1")
    assert scene.get("voltage", "VDD") == 1.8
    assert scene.get_pin_voltage("VDD") == 1.8
    assert scene.get("voltage", "VDD", step="step0", index="1") == 2.5
    assert scene.get_pin_voltage("VDD", step="step0", index="1") == 2.5


def test_timing_scenario_pin_voltage_missing():
    scene = ASICTimingScenarioSchema()
    with pytest.raises(LookupError, match=r"^VDD does not have voltage$"):
        scene.get_pin_voltage("VDD")


def test_timing_scenario_libcorner():
    scene = ASICTimingScenarioSchema()
    assert scene.add_libcorner("slow0")
    assert scene.add_libcorner("slow1")
    assert scene.add_libcorner("slow2", step="step0", index="1")
    assert scene.get("libcorner") == ["slow0", "slow1"]
    assert scene.get_libcorner() == ["slow0", "slow1"]
    assert scene.get("libcorner", step="step0", index="1") == ["slow2"]
    assert scene.get_libcorner(step="step0", index="1") == ["slow2"]


def test_timing_scenario_libcorner_clobber():
    scene = ASICTimingScenarioSchema()
    assert scene.add_libcorner("slow0")
    assert scene.get_libcorner() == ["slow0"]
    assert scene.add_libcorner("slow1", clobber=True)
    assert scene.get_libcorner() == ["slow1"]


def test_timing_scenario_libcorner_clobber_step_index():
    scene = ASICTimingScenarioSchema()
    assert scene.add_libcorner("slow0")
    assert scene.add_libcorner("slow1", step="step0", index="1")
    assert scene.get_libcorner() == ["slow0"]
    assert scene.get_libcorner(step="step0", index="1") == ["slow1"]
    assert scene.add_libcorner("slow2", step="step0", index="1", clobber=True)
    assert scene.get_libcorner() == ["slow0"]
    assert scene.get_libcorner(step="step0", index="1") == ["slow2"]


def test_timing_scenario_pexcorner():
    scene = ASICTimingScenarioSchema()
    assert scene.set_pexcorner("ff")
    assert scene.set_pexcorner("ss", step="step0", index="1")
    assert scene.get("pexcorner") == "ff"
    assert scene.get_pexcorner() == "ff"
    assert scene.get("pexcorner", step="step0", index="1") == "ss"
    assert scene.get_pexcorner(step="step0", index="1") == "ss"


def test_timing_scenario_mode():
    scene = ASICTimingScenarioSchema()
    assert scene.set_mode("run")
    assert scene.set_mode("test", step="step0", index="1")
    assert scene.get("mode") == "run"
    assert scene.get_mode() == "run"
    assert scene.get("mode", step="step0", index="1") == "test"
    assert scene.get_mode(step="step0", index="1") == "test"


def test_timing_scenario_opcond():
    scene = ASICTimingScenarioSchema()
    assert scene.set_opcond("op0")
    assert scene.set_opcond("op1", step="step0", index="1")
    assert scene.get("opcond") == "op0"
    assert scene.get_opcond() == "op0"
    assert scene.get("opcond", step="step0", index="1") == "op1"
    assert scene.get_opcond(step="step0", index="1") == "op1"


def test_timing_scenario_temperature():
    scene = ASICTimingScenarioSchema()
    assert scene.set_temperature(125.0)
    assert scene.set_temperature(-40, step="step0", index="1")
    assert scene.get("temperature") == 125.0
    assert scene.get_temperature() == 125.0
    assert scene.get("temperature", step="step0", index="1") == -40.0
    assert scene.get_temperature(step="step0", index="1") == -40.0


def test_timing_scenario_check():
    scene = ASICTimingScenarioSchema()
    assert scene.add_check("setup")
    assert scene.add_check("hold", step="step0", index="1")
    assert scene.get("check") == ["setup"]
    assert scene.get_check() == ["setup"]
    assert scene.get("check", step="step0", index="1") == ["hold"]
    assert scene.get_check(step="step0", index="1") == ["hold"]


def test_timing_scenario_check_clobber():
    scene = ASICTimingScenarioSchema()
    assert scene.add_check("setup")
    assert scene.get_check() == ["setup"]
    assert scene.add_check("hold", clobber=True)
    assert scene.get_check() == ["hold"]


def test_timing_scenario_check_clobber_step_index():
    scene = ASICTimingScenarioSchema()
    assert scene.add_check("setup")
    assert scene.add_check("hold", step="step0", index="1")
    assert scene.get_check() == ["setup"]
    assert scene.get_check(step="step0", index="1") == ["hold"]
    assert scene.add_check("power", step="step0", index="1", clobber=True)
    assert scene.get_check() == ["setup"]
    assert scene.get_check(step="step0", index="1") == ["power"]


def test_timing_scenario_sdcfileset_invalid_type_design():
    root = ASICTimingConstraintSchema()
    scene = root.make_scenario("testscenario")

    scene.set_mode("testmode")

    with pytest.raises(TypeError, match=r"^design must be a design object or string$"):
        scene.add_sdcfileset(1.0, "fileset")


def test_timing_scenario_sdcfileset_invalid_type_fileset():
    root = ASICTimingConstraintSchema()
    scene = root.make_scenario("testscenario")

    scene.set_mode("testmode")

    with pytest.raises(TypeError, match=r"^fileset must be a string$"):
        scene.add_sdcfileset("test", 1.0)


def test_timing_scenario_sdcfileset_design_obj():
    root = ASICTimingConstraintSchema()
    scene = root.make_scenario("testscenario")

    scene.set_mode("testmode")

    design = Design("test")
    assert scene.add_sdcfileset(design, "rtl")
    assert root.get("mode", "testmode", "sdcfileset") == [("test", "rtl")]
    assert scene.get_sdcfileset() == [("test", "rtl")]


def test_timing_scenario_sdcfileset_design_str():
    root = ASICTimingConstraintSchema()
    scene = root.make_scenario("testscenario")

    scene.set_mode("testmode")

    assert scene.add_sdcfileset("test", "rtl")
    assert root.get("mode", "testmode", "sdcfileset") == [("test", "rtl")]
    assert scene.get_sdcfileset() == [("test", "rtl")]


def test_timing_scenario_sdcfileset_design_step_index():
    root = ASICTimingConstraintSchema()
    scene = root.make_scenario("testscenario")

    scene.set_mode("testmode")

    assert scene.add_sdcfileset("test", "rtl")
    assert scene.add_sdcfileset("test1", "rtl1", step="step0", index="1")
    assert root.get("mode", "testmode", "sdcfileset") == [("test", "rtl")]
    assert scene.get_sdcfileset() == [("test", "rtl")]
    assert root.get("mode", "testmode", "sdcfileset", step="step0", index="1") == \
        [("test1", "rtl1")]
    assert scene.get_sdcfileset(step="step0", index="1") == [("test1", "rtl1")]


def test_timing_scenario_sdcfileset_design_clobber():
    root = ASICTimingConstraintSchema()
    scene = root.make_scenario("testscenario")

    scene.set_mode("testmode")

    assert scene.add_sdcfileset("test", "rtl")
    assert scene.add_sdcfileset("test1", "rtl1", step="step0", index="1")
    assert scene.get_sdcfileset() == [("test", "rtl")]
    assert scene.get_sdcfileset(step="step0", index="1") == [("test1", "rtl1")]
    assert scene.add_sdcfileset("test1", "rtl", step="step0", index="1", clobber=True)
    assert scene.get_sdcfileset() == [("test", "rtl")]
    assert scene.get_sdcfileset(step="step0", index="1") == [("test1", "rtl")]


def test_timing_constraint_keys():
    assert ASICTimingConstraintSchema().allkeys() == set([
        ('scenario', 'default', 'check',),
        ('scenario', 'default', 'libcorner',),
        ('scenario', 'default', 'mode',),
        ('scenario', 'default', 'opcond',),
        ('scenario', 'default', 'pexcorner',),
        ('scenario', 'default', 'temperature',),
        ('scenario', 'default', 'voltage', 'default',),
        ('mode', 'default', 'sdcfileset',),
    ])


def test_timing_constraint_get_scenarios_empty():
    assert ASICTimingConstraintSchema().get_scenario() == {}


def test_timing_constraint_get_scenarios_missing():
    with pytest.raises(LookupError, match=r"^notfound is not defined$"):
        ASICTimingConstraintSchema().get_scenario("notfound")


def test_timing_constraint_add_scenario_invalid_type():
    with pytest.raises(TypeError, match=r"^scenario must be a timing scenario object$"):
        ASICTimingConstraintSchema().add_scenario(ASICTimingConstraintSchema())


def test_timing_constraint_add_scenario_unnamed():
    with pytest.raises(ValueError, match=r"^scenario must have a name$"):
        ASICTimingConstraintSchema().add_scenario(ASICTimingScenarioSchema())


def test_timing_constraint_add_scenario():
    scene = ASICTimingScenarioSchema("slow")
    schema = ASICTimingConstraintSchema()

    schema.add_scenario(scene)
    assert schema.getkeys("scenario") == ("slow",)
    assert schema.get_scenario("slow") is scene


def test_timing_constraint_get_scenario():
    scene_s = ASICTimingScenarioSchema("slow")
    scene_f = ASICTimingScenarioSchema("fast")
    schema = ASICTimingConstraintSchema()

    schema.add_scenario(scene_s)
    schema.add_scenario(scene_f)
    assert schema.getkeys("scenario") == ("fast", "slow")
    assert schema.get_scenario() == {
        "slow": scene_s,
        "fast": scene_f
    }


def test_timing_constraint_make_scenario_illegal():
    with pytest.raises(ValueError, match=r"^scenario name is required$"):
        ASICTimingConstraintSchema().make_scenario(None)


def test_timing_constraint_make_scenario_exists():
    schema = ASICTimingConstraintSchema()

    schema.add_scenario(ASICTimingScenarioSchema("slow"))
    with pytest.raises(LookupError, match=r"^slow scenario already exists$"):
        schema.make_scenario("slow")


def test_timing_constraint_make_scenario():
    schema = ASICTimingConstraintSchema()

    constraint = schema.make_scenario("slow")
    assert isinstance(constraint, ASICTimingScenarioSchema)
    assert constraint.name == "slow"
    assert schema.get("scenario", "slow", field="schema") is constraint


def test_timing_constraint_remove_scenario_illegal():
    with pytest.raises(ValueError, match=r"^scenario name is required$"):
        ASICTimingConstraintSchema().remove_scenario(None)


def test_timing_constraint_remove_scenario_not_found():
    assert ASICTimingConstraintSchema().remove_scenario("slow") is False


def test_timing_constraint_remove_scenario():
    schema = ASICTimingConstraintSchema()

    schema.make_scenario("slow")
    assert schema.getkeys("scenario") == ("slow",)
    assert schema.remove_scenario("slow") is True
    assert schema.getkeys("scenario") == tuple()


def test_timing_constraint_copy_scenario():
    schema = ASICTimingConstraintSchema()

    schema.make_scenario("slow")
    new_obj = schema.copy_scenario("slow", "fast")
    assert new_obj.name == "fast"
    assert schema.getkeys("scenario") == ("fast", "slow")


def test_timing_constraint_copy_scenario_samename():
    schema = ASICTimingConstraintSchema()

    schema.make_scenario("slow")
    with pytest.raises(ValueError, match=r"^slow already exists$"):
        schema.copy_scenario("slow", "slow")


def test_timing_constraint_copy_scenario_no_insert():
    schema = ASICTimingConstraintSchema()

    schema.make_scenario("slow")
    new_obj = schema.copy_scenario("slow", "fast", insert=False)
    assert new_obj.name == "fast"
    assert schema.getkeys("scenario") == ("slow",)


def test_timing_constraint_get_modes_empty():
    assert ASICTimingConstraintSchema().get_mode() == {}


def test_timing_constraint_get_modes_missing():
    with pytest.raises(LookupError, match=r"^notfound is not defined$"):
        ASICTimingConstraintSchema().get_mode("notfound")


def test_timing_constraint_add_mode_invalid_type():
    with pytest.raises(TypeError, match=r"^mode must be a timing mode object$"):
        ASICTimingConstraintSchema().add_mode(ASICTimingConstraintSchema())


def test_timing_constraint_add_mode_unnamed():
    with pytest.raises(ValueError, match=r"^mode must have a name$"):
        ASICTimingConstraintSchema().add_mode(TimingModeSchema())


def test_timing_constraint_add_mode():
    mode = TimingModeSchema("slow")
    schema = ASICTimingConstraintSchema()

    schema.add_mode(mode)
    assert schema.getkeys("mode") == ("slow",)
    assert schema.get_mode("slow") is mode


def test_timing_constraint_get_mode():
    mode_s = TimingModeSchema("slow")
    mode_f = TimingModeSchema("fast")
    schema = ASICTimingConstraintSchema()

    schema.add_mode(mode_s)
    schema.add_mode(mode_f)
    assert schema.getkeys("mode") == ("fast", "slow")
    assert schema.get_mode() == {
        "slow": mode_s,
        "fast": mode_f
    }


def test_timing_constraint_make_mode_illegal():
    with pytest.raises(ValueError, match=r"^mode name is required$"):
        ASICTimingConstraintSchema().make_mode(None)


def test_timing_constraint_make_mode_exists():
    schema = ASICTimingConstraintSchema()

    schema.add_mode(TimingModeSchema("slow"))
    with pytest.raises(LookupError, match=r"^slow mode already exists$"):
        schema.make_mode("slow")


def test_timing_constraint_make_mode():
    schema = ASICTimingConstraintSchema()

    constraint = schema.make_mode("slow")
    assert isinstance(constraint, TimingModeSchema)
    assert constraint.name == "slow"
    assert schema.get("mode", "slow", field="schema") is constraint


def test_timing_constraint_remove_mode_illegal():
    with pytest.raises(ValueError, match=r"^mode name is required$"):
        ASICTimingConstraintSchema().remove_mode(None)


def test_timing_constraint_remove_mode_not_found():
    assert ASICTimingConstraintSchema().remove_mode("slow") is False


def test_timing_constraint_remove_mode():
    schema = ASICTimingConstraintSchema()

    schema.make_mode("slow")
    assert schema.getkeys("mode") == ("slow",)
    assert schema.remove_mode("slow") is True
    assert schema.getkeys("mode") == tuple()


def test_timing_constraint_copy_mode():
    schema = ASICTimingConstraintSchema()

    schema.make_mode("slow")
    new_obj = schema.copy_mode("slow", "fast")
    assert new_obj.name == "fast"
    assert schema.getkeys("mode") == ("fast", "slow")


def test_timing_constraint_copy_mode_samename():
    schema = ASICTimingConstraintSchema()

    schema.make_mode("slow")
    with pytest.raises(ValueError, match=r"^slow already exists$"):
        schema.copy_mode("slow", "slow")


def test_timing_constraint_copy_mode_no_insert():
    schema = ASICTimingConstraintSchema()

    schema.make_mode("slow")
    new_obj = schema.copy_mode("slow", "fast", insert=False)
    assert new_obj.name == "fast"
    assert schema.getkeys("mode") == ("slow",)
