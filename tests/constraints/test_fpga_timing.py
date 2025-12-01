import pytest

from siliconcompiler.schema import PerNode, Scope

from siliconcompiler.constraints import FPGATimingScenarioSchema, FPGATimingConstraintSchema, \
    TimingModeSchema


def test_timing_scenario_keys():
    assert FPGATimingScenarioSchema().allkeys() == set([
        ('mode',),
    ])


@pytest.mark.parametrize("key", FPGATimingScenarioSchema().allkeys())
def test_timing_scenario_key_params(key):
    param = FPGATimingScenarioSchema().get(*key, field=None)
    assert param.get(field="pernode") == PerNode.OPTIONAL
    assert param.get(field="scope") == Scope.GLOBAL


def test_timing_scenario_mode():
    scene = FPGATimingScenarioSchema()
    assert scene.set_mode("run")
    assert scene.set_mode("test", step="step0", index="1")
    assert scene.get("mode") == "run"
    assert scene.get_mode() == "run"
    assert scene.get("mode", step="step0", index="1") == "test"
    assert scene.get_mode(step="step0", index="1") == "test"


def test_timing_constraint_keys():
    assert FPGATimingConstraintSchema().allkeys() == set([
        ('scenario', 'default', 'mode',),
        ('mode', 'default', 'sdcfileset',),
    ])


def test_timing_constraint_get_scenarios_empty():
    assert FPGATimingConstraintSchema().get_scenario() == {}


def test_timing_constraint_get_scenarios_missing():
    with pytest.raises(LookupError, match=r"^notfound is not defined$"):
        FPGATimingConstraintSchema().get_scenario("notfound")


def test_timing_constraint_add_scenario_invalid_type():
    with pytest.raises(TypeError, match=r"^scenario must be a timing scenario object$"):
        FPGATimingConstraintSchema().add_scenario(FPGATimingConstraintSchema())


def test_timing_constraint_add_scenario_unnamed():
    with pytest.raises(ValueError, match=r"^scenario must have a name$"):
        FPGATimingConstraintSchema().add_scenario(FPGATimingScenarioSchema())


def test_timing_constraint_add_scenario():
    scene = FPGATimingScenarioSchema("slow")
    schema = FPGATimingConstraintSchema()

    schema.add_scenario(scene)
    assert schema.getkeys("scenario") == ("slow",)
    assert schema.get_scenario("slow") is scene


def test_timing_constraint_get_scenario():
    scene_s = FPGATimingScenarioSchema("slow")
    scene_f = FPGATimingScenarioSchema("fast")
    schema = FPGATimingConstraintSchema()

    schema.add_scenario(scene_s)
    schema.add_scenario(scene_f)
    assert schema.getkeys("scenario") == ("fast", "slow")
    assert schema.get_scenario() == {
        "slow": scene_s,
        "fast": scene_f
    }


def test_timing_constraint_make_scenario_illegal():
    with pytest.raises(ValueError, match=r"^scenario name is required$"):
        FPGATimingConstraintSchema().make_scenario(None)


def test_timing_constraint_make_scenario_exists():
    schema = FPGATimingConstraintSchema()

    schema.add_scenario(FPGATimingScenarioSchema("slow"))
    with pytest.raises(LookupError, match=r"^slow scenario already exists$"):
        schema.make_scenario("slow")


def test_timing_constraint_make_scenario():
    schema = FPGATimingConstraintSchema()

    constraint = schema.make_scenario("slow")
    assert isinstance(constraint, FPGATimingScenarioSchema)
    assert constraint.name == "slow"
    assert schema.get("scenario", "slow", field="schema") is constraint


def test_timing_constraint_remove_scenario_illegal():
    with pytest.raises(ValueError, match=r"^scenario name is required$"):
        FPGATimingConstraintSchema().remove_scenario(None)


def test_timing_constraint_remove_scenario_not_found():
    assert FPGATimingConstraintSchema().remove_scenario("slow") is False


def test_timing_constraint_remove_scenario():
    schema = FPGATimingConstraintSchema()

    schema.make_scenario("slow")
    assert schema.getkeys("scenario") == ("slow",)
    assert schema.remove_scenario("slow") is True
    assert schema.getkeys("scenario") == tuple()


def test_timing_constraint_copy_scenario():
    schema = FPGATimingConstraintSchema()

    schema.make_scenario("slow")
    new_obj = schema.copy_scenario("slow", "fast")
    assert new_obj.name == "fast"
    assert schema.getkeys("scenario") == ("fast", "slow")


def test_timing_constraint_copy_scenario_samename():
    schema = FPGATimingConstraintSchema()

    schema.make_scenario("slow")
    with pytest.raises(ValueError, match=r"^slow already exists$"):
        schema.copy_scenario("slow", "slow")


def test_timing_constraint_copy_scenario_no_insert():
    schema = FPGATimingConstraintSchema()

    schema.make_scenario("slow")
    new_obj = schema.copy_scenario("slow", "fast", insert=False)
    assert new_obj.name == "fast"
    assert schema.getkeys("scenario") == ("slow",)


def test_timing_constraint_get_modes_empty():
    assert FPGATimingConstraintSchema().get_mode() == {}


def test_timing_constraint_get_modes_missing():
    with pytest.raises(LookupError, match=r"^notfound is not defined$"):
        FPGATimingConstraintSchema().get_mode("notfound")


def test_timing_constraint_add_mode_invalid_type():
    with pytest.raises(TypeError, match=r"^mode must be a timing mode object$"):
        FPGATimingConstraintSchema().add_mode(FPGATimingConstraintSchema())


def test_timing_constraint_add_mode_unnamed():
    with pytest.raises(ValueError, match=r"^mode must have a name$"):
        FPGATimingConstraintSchema().add_mode(TimingModeSchema())


def test_timing_constraint_add_mode():
    mode = TimingModeSchema("slow")
    schema = FPGATimingConstraintSchema()

    schema.add_mode(mode)
    assert schema.getkeys("mode") == ("slow",)
    assert schema.get_mode("slow") is mode


def test_timing_constraint_get_mode():
    mode_s = TimingModeSchema("slow")
    mode_f = TimingModeSchema("fast")
    schema = FPGATimingConstraintSchema()

    schema.add_mode(mode_s)
    schema.add_mode(mode_f)
    assert schema.getkeys("mode") == ("fast", "slow")
    assert schema.get_mode() == {
        "slow": mode_s,
        "fast": mode_f
    }


def test_timing_constraint_make_mode_illegal():
    with pytest.raises(ValueError, match=r"^mode name is required$"):
        FPGATimingConstraintSchema().make_mode(None)


def test_timing_constraint_make_mode_exists():
    schema = FPGATimingConstraintSchema()

    schema.add_mode(TimingModeSchema("slow"))
    with pytest.raises(LookupError, match=r"^slow mode already exists$"):
        schema.make_mode("slow")


def test_timing_constraint_make_mode():
    schema = FPGATimingConstraintSchema()

    constraint = schema.make_mode("slow")
    assert isinstance(constraint, TimingModeSchema)
    assert constraint.name == "slow"
    assert schema.get("mode", "slow", field="schema") is constraint


def test_timing_constraint_remove_mode_illegal():
    with pytest.raises(ValueError, match=r"^mode name is required$"):
        FPGATimingConstraintSchema().remove_mode(None)


def test_timing_constraint_remove_mode_not_found():
    assert FPGATimingConstraintSchema().remove_mode("slow") is False


def test_timing_constraint_remove_mode():
    schema = FPGATimingConstraintSchema()

    schema.make_mode("slow")
    assert schema.getkeys("mode") == ("slow",)
    assert schema.remove_mode("slow") is True
    assert schema.getkeys("mode") == tuple()


def test_timing_constraint_copy_mode():
    schema = FPGATimingConstraintSchema()

    schema.make_mode("slow")
    new_obj = schema.copy_mode("slow", "fast")
    assert new_obj.name == "fast"
    assert schema.getkeys("mode") == ("fast", "slow")


def test_timing_constraint_copy_mode_samename():
    schema = FPGATimingConstraintSchema()

    schema.make_mode("slow")
    with pytest.raises(ValueError, match=r"^slow already exists$"):
        schema.copy_mode("slow", "slow")


def test_timing_constraint_copy_mode_no_insert():
    schema = FPGATimingConstraintSchema()

    schema.make_mode("slow")
    new_obj = schema.copy_mode("slow", "fast", insert=False)
    assert new_obj.name == "fast"
    assert schema.getkeys("mode") == ("slow",)
