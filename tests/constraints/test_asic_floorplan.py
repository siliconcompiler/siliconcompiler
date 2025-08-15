import pytest

from siliconcompiler.schema import PerNode, Scope

from siliconcompiler.constraints import ASICAreaConstraint


def test_keys():
    assert ASICAreaConstraint().allkeys() == set([
        ('aspectratio',),
        ('corearea',),
        ('coremargin',),
        ('density',),
        ('diearea',)
    ])


@pytest.mark.parametrize("key", ASICAreaConstraint().allkeys())
def test_key_params(key):
    param = ASICAreaConstraint().get(*key, field=None)
    assert param.get(field="pernode") == PerNode.OPTIONAL
    assert param.get(field="scope") == Scope.GLOBAL


def test_aspectratio_illegal():
    with pytest.raises(TypeError, match="aspectratio must be a number"):
        ASICAreaConstraint().set_aspectratio("abc")


def test_aspectratio_negative():
    with pytest.raises(ValueError, match="aspectratio cannot be zero or negative"):
        ASICAreaConstraint().set_aspectratio(-1)


def test_aspectratio_zero():
    with pytest.raises(ValueError, match="aspectratio cannot be zero or negative"):
        ASICAreaConstraint().set_aspectratio(0)


def test_aspectratio():
    schema = ASICAreaConstraint()

    assert schema.get_aspectratio() == 1.0
    assert schema.set_aspectratio(1.5)
    assert schema.get("aspectratio") == 1.5
    assert schema.get_aspectratio() == 1.5


def test_aspectratio_step_index():
    schema = ASICAreaConstraint()

    assert schema.get_aspectratio() == 1.0
    assert schema.set_aspectratio(1.5, step="step0", index="0")
    assert schema.get("aspectratio", step="step0", index="0") == 1.5
    assert schema.get_aspectratio() == 1.0
    assert schema.get_aspectratio(step="step0", index="0") == 1.5


def test_coremargin_illegal():
    with pytest.raises(TypeError, match="coremargin must be a number"):
        ASICAreaConstraint().set_coremargin("abc")


def test_coremargin_negative():
    with pytest.raises(ValueError, match="coremargin cannot be negative"):
        ASICAreaConstraint().set_coremargin(-1)


def test_coremargin():
    schema = ASICAreaConstraint()

    assert schema.set_coremargin(1.5)
    assert schema.get("coremargin") == 1.5
    assert schema.get_coremargin() == 1.5


def test_coremargin_step_index():
    schema = ASICAreaConstraint()

    assert schema.set_coremargin(1.5, step="step0", index="0")
    assert schema.get("coremargin", step="step0", index="0") == 1.5
    assert schema.get_coremargin(step="step0", index="0") == 1.5


def test_density_illegal():
    with pytest.raises(TypeError, match="density must be a number"):
        ASICAreaConstraint().set_density("abc")


def test_density_negative():
    with pytest.raises(ValueError, match=r"density must be between \(0, 100\]"):
        ASICAreaConstraint().set_density(-1)


def test_density_zero():
    with pytest.raises(ValueError, match=r"density must be between \(0, 100\]"):
        ASICAreaConstraint().set_density(0)


def test_density_gt_100():
    with pytest.raises(ValueError, match=r"density must be between \(0, 100\]"):
        ASICAreaConstraint().set_density(101)


def test_density_100():
    assert ASICAreaConstraint().set_density(100)


def test_density():
    schema = ASICAreaConstraint()

    assert schema.set_density(1.5)
    assert schema.get("density") == 1.5
    assert schema.get_density() == 1.5


def test_density_step_index():
    schema = ASICAreaConstraint()

    assert schema.set_density(1.5, step="step0", index="0")
    assert schema.get("density", step="step0", index="0") == 1.5
    assert schema.get_density(step="step0", index="0") == 1.5


def test_density_aspectratio_coremargin_step_index():
    schema = ASICAreaConstraint()

    assert schema.set_density(1.5, aspectratio=2.0, coremargin=5.0, step="step0", index="0")
    assert schema.get("density", step="step0", index="0") == 1.5
    assert schema.get("aspectratio", step="step0", index="0") == 2.0
    assert schema.get("coremargin", step="step0", index="0") == 5.0
    assert schema.get("aspectratio") == 1.0
    assert schema.get("coremargin") is None


def test_corearea_rectangle_illegal_height():
    with pytest.raises(TypeError, match="height must be a number"):
        ASICAreaConstraint().set_corearea_rectangle("abc", "abc", "abc")


def test_corearea_rectangle_illegal_width():
    with pytest.raises(TypeError, match="width must be a number"):
        ASICAreaConstraint().set_corearea_rectangle(100.0, "abc", "abc")


def test_corearea_rectangle_illegal_margin():
    with pytest.raises(TypeError, match="coremargin must be a number or a tuple of two numbers"):
        ASICAreaConstraint().set_corearea_rectangle(100.0, 100.0, "abc")


def test_corearea_rectangle_illegal_negative_height():
    with pytest.raises(ValueError, match="height must be greater than zero"):
        ASICAreaConstraint().set_corearea_rectangle(-100.0, 100.0, 2.0)


def test_corearea_rectangle_illegal_negative_width():
    with pytest.raises(ValueError, match="width must be greater than zero"):
        ASICAreaConstraint().set_corearea_rectangle(100.0, -100.0, 2.0)


def test_corearea_rectangle_illegal_negative_margin():
    with pytest.raises(ValueError, match="x margin cannot be negative"):
        ASICAreaConstraint().set_corearea_rectangle(100.0, 100.0, -2.0)


def test_corearea_rectangle_illegal_negative_xmargin():
    with pytest.raises(ValueError, match="x margin cannot be negative"):
        ASICAreaConstraint().set_corearea_rectangle(100.0, 100.0, (-2.0, 2))


def test_corearea_rectangle_illegal_extra_margin():
    with pytest.raises(ValueError, match="coremargin must be a number or a tuple of two numbers"):
        ASICAreaConstraint().set_corearea_rectangle(100.0, 100.0, (2.0, 2, 2.0))


def test_corearea_rectangle_illegal_negative_ymargin():
    with pytest.raises(ValueError, match="y margin cannot be negative"):
        ASICAreaConstraint().set_corearea_rectangle(100.0, 100.0, (2, -2.0))


def test_corearea_rectangle_illegal_zero_height():
    with pytest.raises(ValueError, match="height must be greater than zero"):
        ASICAreaConstraint().set_corearea_rectangle(0.0, 100.0, 2.0)


def test_corearea_rectangle_illegal_zero_width():
    with pytest.raises(ValueError, match="width must be greater than zero"):
        ASICAreaConstraint().set_corearea_rectangle(100.0, 0, 2.0)


def test_corearea_rectangle_illegal_extra_xmargin():
    with pytest.raises(ValueError,
                       match="x margin is greater than or equal to the die width"):
        ASICAreaConstraint().set_corearea_rectangle(100.0, 100.0, (50.0, 2))


def test_corearea_rectangle_illegal_extra_ymargin():
    with pytest.raises(ValueError,
                       match="y margin is greater than or equal to the die height"):
        ASICAreaConstraint().set_corearea_rectangle(100.0, 100.0, (2, 50.0))


def test_corearea_rectangle():
    schema = ASICAreaConstraint()
    assert schema.set_corearea_rectangle(100.0, 150.0, (2, 5.0))
    assert schema.get("corearea") == [(2.0, 5.0), (148.0, 95.0)]
    assert schema.get_corearea() == [(2.0, 5.0), (148.0, 95.0)]


def test_corearea_rectangle_zero_margin():
    schema = ASICAreaConstraint()
    assert schema.set_corearea_rectangle(100.0, 100.0, 0)
    assert schema.get("corearea") == [(0.0, 0.0), (100.0, 100.0)]
    assert schema.get_corearea() == [(0.0, 0.0), (100.0, 100.0)]


def test_corearea_rectangle_step_index():
    schema = ASICAreaConstraint()
    assert schema.set_corearea_rectangle(100.0, 100.0, 5.0)
    assert schema.set_corearea_rectangle(100.0, 100.0, 2.0, step="step0", index="0")
    assert schema.get("corearea") == [(5.0, 5.0), (95.0, 95.0)]
    assert schema.get_corearea() == [(5.0, 5.0), (95.0, 95.0)]
    assert schema.get("corearea", step="step0", index="0") == [(2.0, 2.0), (98.0, 98.0)]
    assert schema.get_corearea(step="step0", index="0") == [(2.0, 2.0), (98.0, 98.0)]


def test_diearea_rectangle_illegal_height():
    with pytest.raises(TypeError, match="height must be a number"):
        ASICAreaConstraint().set_diearea_rectangle("abc", "abc", "abc")


def test_diearea_rectangle_illegal_width():
    with pytest.raises(TypeError, match="width must be a number"):
        ASICAreaConstraint().set_diearea_rectangle(100.0, "abc", "abc")


def test_diearea_rectangle_illegal_negative_height():
    with pytest.raises(ValueError, match="height must be greater than zero"):
        ASICAreaConstraint().set_diearea_rectangle(-100.0, 100.0, 2.0)


def test_diearea_rectangle_illegal_negative_width():
    with pytest.raises(ValueError, match="width must be greater than zero"):
        ASICAreaConstraint().set_diearea_rectangle(100.0, -100.0, 2.0)


def test_diearea_rectangle_no_margin():
    schema = ASICAreaConstraint()
    assert schema.set_diearea_rectangle(100.0, 150.0)
    assert schema.get("diearea") == [(0.0, 0.0), (150.0, 100.0)]
    assert schema.get_diearea() == [(0.0, 0.0), (150.0, 100.0)]
    assert schema.get_corearea() == []


def test_diearea_rectangle():
    schema = ASICAreaConstraint()
    assert schema.set_diearea_rectangle(100.0, 150.0, (2, 5.0))
    assert schema.get("diearea") == [(0.0, 0.0), (150.0, 100.0)]
    assert schema.get_diearea() == [(0.0, 0.0), (150.0, 100.0)]
    assert schema.get("corearea") == [(2.0, 5.0), (148.0, 95.0)]
    assert schema.get_corearea() == [(2.0, 5.0), (148.0, 95.0)]


def test_diearea_rectangle_zero_margin():
    schema = ASICAreaConstraint()
    assert schema.set_diearea_rectangle(100.0, 100.0, 0)
    assert schema.get("diearea") == [(0.0, 0.0), (100.0, 100.0)]
    assert schema.get_diearea() == [(0.0, 0.0), (100.0, 100.0)]
    assert schema.get("corearea") == [(0.0, 0.0), (100.0, 100.0)]
    assert schema.get_corearea() == [(0.0, 0.0), (100.0, 100.0)]


def test_diearea_rectangle_step_index():
    schema = ASICAreaConstraint()
    assert schema.set_diearea_rectangle(100.0, 100.0, 5.0)
    assert schema.set_diearea_rectangle(100.0, 150.0, 2.0, step="step0", index="0")
    assert schema.get("diearea") == [(0.0, 0.0), (100.0, 100.0)]
    assert schema.get_diearea() == [(0.0, 0.0), (100.0, 100.0)]
    assert schema.get("corearea") == [(5.0, 5.0), (95.0, 95.0)]
    assert schema.get_corearea() == [(5.0, 5.0), (95.0, 95.0)]
    assert schema.get("diearea", step="step0", index="0") == [(0.0, 0.0), (150.0, 100.0)]
    assert schema.get_diearea(step="step0", index="0") == [(0.0, 0.0), (150.0, 100.0)]
    assert schema.get("corearea", step="step0", index="0") == [(2.0, 2.0), (148.0, 98.0)]
    assert schema.get_corearea(step="step0", index="0") == [(2.0, 2.0), (148.0, 98.0)]


def test_set_diearea():
    schema = ASICAreaConstraint()
    assert schema.set_diearea([(0, 0), (10, 10), (20, 20), (20, 0), (0, 0)])
    assert schema.get_diearea() == [(0, 0), (10, 10), (20, 20), (20, 0), (0, 0)]


def test_set_corearea():
    schema = ASICAreaConstraint()
    assert schema.set_corearea([(0, 0), (10, 10), (20, 20), (20, 0), (0, 0)])
    assert schema.get_corearea() == [(0, 0), (10, 10), (20, 20), (20, 0), (0, 0)]


@pytest.mark.parametrize("shape,expect", [
    ([(0, 0), (10, 10)], 100),
    ([(0, 0), (0, 20), (10, 20), (10, 10), (20, 10), (20, 0)], 300),
])
def test_calc_area(shape, expect):
    schema = ASICAreaConstraint()
    schema.set_diearea(shape)

    assert schema.calc_diearea() == expect


@pytest.mark.parametrize("shape,expect", [
    ([(0, 0), (10, 10)], 100),
    ([(0, 0), (0, 20), (10, 20), (10, 10), (20, 10), (20, 0)], 300),
])
def test_calc_area_with_step_index(shape, expect):
    schema = ASICAreaConstraint()
    schema.set_diearea([(0, 0), (100, 100)])
    schema.set_diearea(shape, step="step", index="index")

    assert schema.calc_diearea() == 10000
    assert schema.calc_diearea(step="step", index="index") == expect
