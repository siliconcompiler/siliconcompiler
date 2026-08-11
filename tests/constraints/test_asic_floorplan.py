import math
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
    with pytest.raises(TypeError, match=r"^aspectratio must be a number$"):
        ASICAreaConstraint().set_aspectratio("abc")


def test_aspectratio_negative():
    with pytest.raises(ValueError, match=r"^aspectratio cannot be zero or negative$"):
        ASICAreaConstraint().set_aspectratio(-1)


def test_aspectratio_zero():
    with pytest.raises(ValueError, match=r"^aspectratio cannot be zero or negative$"):
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
    with pytest.raises(TypeError, match=r"^coremargin must be a number$"):
        ASICAreaConstraint().set_coremargin("abc")


def test_coremargin_negative():
    with pytest.raises(ValueError, match=r"^coremargin cannot be negative$"):
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
    with pytest.raises(TypeError, match=r"^density must be a number$"):
        ASICAreaConstraint().set_density("abc")


def test_density_negative():
    with pytest.raises(ValueError, match=r"^density must be between \(0, 100\]$"):
        ASICAreaConstraint().set_density(-1)


def test_density_zero():
    with pytest.raises(ValueError, match=r"^density must be between \(0, 100\]$"):
        ASICAreaConstraint().set_density(0)


def test_density_gt_100():
    with pytest.raises(ValueError, match=r"^density must be between \(0, 100\]$"):
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
    with pytest.raises(TypeError, match=r"^height must be a number$"):
        ASICAreaConstraint().set_corearea_rectangle("abc", "abc", "abc")


def test_corearea_rectangle_illegal_width():
    with pytest.raises(TypeError, match=r"^width must be a number$"):
        ASICAreaConstraint().set_corearea_rectangle(100.0, "abc", "abc")


def test_corearea_rectangle_illegal_margin():
    with pytest.raises(TypeError, match=r"^coremargin must be a number or a tuple of two numbers$"):
        ASICAreaConstraint().set_corearea_rectangle(100.0, 100.0, "abc")


def test_corearea_rectangle_illegal_negative_height():
    with pytest.raises(ValueError, match=r"^height must be greater than zero$"):
        ASICAreaConstraint().set_corearea_rectangle(-100.0, 100.0, 2.0)


def test_corearea_rectangle_illegal_negative_width():
    with pytest.raises(ValueError, match=r"^width must be greater than zero$"):
        ASICAreaConstraint().set_corearea_rectangle(100.0, -100.0, 2.0)


def test_corearea_rectangle_illegal_negative_margin():
    with pytest.raises(ValueError, match=r"^x margin cannot be negative$"):
        ASICAreaConstraint().set_corearea_rectangle(100.0, 100.0, -2.0)


def test_corearea_rectangle_illegal_negative_xmargin():
    with pytest.raises(ValueError, match=r"^x margin cannot be negative$"):
        ASICAreaConstraint().set_corearea_rectangle(100.0, 100.0, (-2.0, 2))


def test_corearea_rectangle_illegal_extra_margin():
    with pytest.raises(ValueError,
                       match=r"^coremargin must be a number or a tuple of two numbers$"):
        ASICAreaConstraint().set_corearea_rectangle(100.0, 100.0, (2.0, 2, 2.0))


def test_corearea_rectangle_illegal_negative_ymargin():
    with pytest.raises(ValueError, match=r"^y margin cannot be negative$"):
        ASICAreaConstraint().set_corearea_rectangle(100.0, 100.0, (2, -2.0))


def test_corearea_rectangle_illegal_zero_height():
    with pytest.raises(ValueError, match=r"^height must be greater than zero$"):
        ASICAreaConstraint().set_corearea_rectangle(0.0, 100.0, 2.0)


def test_corearea_rectangle_illegal_zero_width():
    with pytest.raises(ValueError, match=r"^width must be greater than zero$"):
        ASICAreaConstraint().set_corearea_rectangle(100.0, 0, 2.0)


def test_corearea_rectangle_illegal_extra_xmargin():
    with pytest.raises(ValueError,
                       match=r"^x margin is greater than or equal to the die width$"):
        ASICAreaConstraint().set_corearea_rectangle(100.0, 100.0, (50.0, 2))


def test_corearea_rectangle_illegal_extra_ymargin():
    with pytest.raises(ValueError,
                       match=r"^y margin is greater than or equal to the die height$"):
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
    with pytest.raises(TypeError, match=r"^height must be a number$"):
        ASICAreaConstraint().set_diearea_rectangle("abc", "abc", "abc")


def test_diearea_rectangle_illegal_width():
    with pytest.raises(TypeError, match=r"^width must be a number$"):
        ASICAreaConstraint().set_diearea_rectangle(100.0, "abc", "abc")


def test_diearea_rectangle_illegal_negative_height():
    with pytest.raises(ValueError, match=r"^height must be greater than zero$"):
        ASICAreaConstraint().set_diearea_rectangle(-100.0, 100.0, 2.0)


def test_diearea_rectangle_illegal_negative_width():
    with pytest.raises(ValueError, match=r"^width must be greater than zero$"):
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


def test_get_dieboundingbox_empty():
    schema = ASICAreaConstraint()
    assert schema.get_dieboundingbox() == ((0.0, 0.0), (0.0, 0.0))


def test_get_dieboundingbox_rectangle():
    schema = ASICAreaConstraint()
    schema.set_diearea([(0, 0), (150, 100)])
    assert schema.get_dieboundingbox() == ((0, 0), (150, 100))


def test_get_dieboundingbox_polygon():
    schema = ASICAreaConstraint()
    schema.set_diearea([(0, 0), (0, 20), (10, 20), (10, 10), (20, 10), (20, 0)])
    assert schema.get_dieboundingbox() == ((0, 0), (20, 20))


@pytest.mark.parametrize("shape,expect", [
    ([(0, 0), (150, 200)], ((0, 0), (150, 200))),
    ([(0, 0), (0, 20), (10, 20), (10, 10), (20, 10), (20, 0)], ((0, 0), (20, 20))),
])
def test_get_dieboundingbox_step_index(shape, expect):
    schema = ASICAreaConstraint()
    schema.set_diearea([(0, 0), (100, 100)])
    schema.set_diearea(shape, step="step0", index="0")
    assert schema.get_dieboundingbox() == ((0, 0), (100, 100))
    assert schema.get_dieboundingbox(step="step0", index="0") == expect


def test_get_diesize_empty():
    schema = ASICAreaConstraint()
    assert schema.get_diesize() == (0.0, 0.0)


def test_get_diesize_rectangle():
    schema = ASICAreaConstraint()
    schema.set_diearea([(0, 0), (150, 100)])
    assert schema.get_diesize() == (150, 100)


def test_get_diesize_polygon():
    schema = ASICAreaConstraint()
    schema.set_diearea([(0, 0), (0, 20), (10, 20), (10, 10), (20, 10), (20, 0)])
    assert schema.get_diesize() == (20, 20)


@pytest.mark.parametrize("shape,expect", [
    ([(0, 0), (150, 200)], (150, 200)),
    ([(0, 0), (0, 20), (10, 20), (10, 10), (20, 10), (20, 0)], (20, 20)),
])
def test_get_diesize_step_index(shape, expect):
    schema = ASICAreaConstraint()
    schema.set_diearea([(0, 0), (100, 100)])
    schema.set_diearea(shape, step="step0", index="0")
    assert schema.get_diesize() == (100, 100)
    assert schema.get_diesize(step="step0", index="0") == expect


def test_get_coreboundingbox_empty():
    schema = ASICAreaConstraint()
    assert schema.get_coreboundingbox() == ((0.0, 0.0), (0.0, 0.0))


def test_get_coreboundingbox_rectangle():
    schema = ASICAreaConstraint()
    schema.set_corearea([(2, 5), (148, 95)])
    assert schema.get_coreboundingbox() == ((2, 5), (148, 95))


def test_get_coreboundingbox_polygon():
    schema = ASICAreaConstraint()
    schema.set_corearea([(0, 0), (0, 20), (10, 20), (10, 10), (20, 10), (20, 0)])
    assert schema.get_coreboundingbox() == ((0, 0), (20, 20))


@pytest.mark.parametrize("shape,expect", [
    ([(2, 5), (148, 195)], ((2, 5), (148, 195))),
    ([(0, 0), (0, 20), (10, 20), (10, 10), (20, 10), (20, 0)], ((0, 0), (20, 20))),
])
def test_get_coreboundingbox_step_index(shape, expect):
    schema = ASICAreaConstraint()
    schema.set_corearea([(0, 0), (100, 100)])
    schema.set_corearea(shape, step="step0", index="0")
    assert schema.get_coreboundingbox() == ((0, 0), (100, 100))
    assert schema.get_coreboundingbox(step="step0", index="0") == expect


def test_get_coresize_empty():
    schema = ASICAreaConstraint()
    assert schema.get_coresize() == (0.0, 0.0)


def test_get_coresize_rectangle():
    schema = ASICAreaConstraint()
    schema.set_corearea([(2, 5), (148, 95)])
    assert schema.get_coresize() == (146, 90)


def test_get_coresize_polygon():
    schema = ASICAreaConstraint()
    schema.set_corearea([(0, 0), (0, 20), (10, 20), (10, 10), (20, 10), (20, 0)])
    assert schema.get_coresize() == (20, 20)


@pytest.mark.parametrize("shape,expect", [
    ([(2, 5), (148, 195)], (146, 190)),
    ([(0, 0), (0, 20), (10, 20), (10, 10), (20, 10), (20, 0)], (20, 20)),
])
def test_get_coresize_step_index(shape, expect):
    schema = ASICAreaConstraint()
    schema.set_corearea([(0, 0), (100, 100)])
    schema.set_corearea(shape, step="step0", index="0")
    assert schema.get_coresize() == (100, 100)
    assert schema.get_coresize(step="step0", index="0") == expect


def test_calc_area_empty():
    schema = ASICAreaConstraint()
    assert schema.calc_diearea() == 0.0


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


def test_calc_floorplan_areas_unset():
    # Nothing to resolve, the floorplan has to be sized from density/aspectratio.
    assert ASICAreaConstraint().calc_floorplan_areas() is None


def test_calc_floorplan_areas_both_set():
    schema = ASICAreaConstraint()
    schema.set_diearea_rectangle(100.0, 150.0, 2.0)
    schema.set_coremargin(25.0)

    # An explicit core area wins over the core margin.
    assert schema.calc_floorplan_areas() == (
        [(0.0, 0.0), (150.0, 100.0)],
        [(2.0, 2.0), (148.0, 98.0)])


def test_calc_floorplan_areas_die_with_margin():
    schema = ASICAreaConstraint()
    schema.set_diearea_rectangle(500.0, 500.0)
    schema.set_coremargin(1.0)

    assert schema.calc_floorplan_areas() == (
        [(0.0, 0.0), (500.0, 500.0)],
        [(1.0, 1.0), (499.0, 499.0)])


def test_calc_floorplan_areas_die_without_margin():
    schema = ASICAreaConstraint()
    schema.set_diearea_rectangle(500.0, 500.0)

    # An unset core margin is a zero margin, the die area is still honored.
    assert schema.calc_floorplan_areas() == (
        [(0.0, 0.0), (500.0, 500.0)],
        [(0.0, 0.0), (500.0, 500.0)])


def test_calc_floorplan_areas_die_polygon_with_margin():
    schema = ASICAreaConstraint()
    # An L shape, wound clockwise, missing its top right corner.
    schema.set_diearea([(0, 0), (0, 200), (200, 200), (200, 100), (300, 100), (300, 0)])
    schema.set_coremargin(5.0)

    # The core follows the die outline. A bounding box inset would have put the
    # core over the missing corner, outside the die.
    assert schema.calc_floorplan_areas() == (
        [(0.0, 0.0), (0.0, 200.0), (200.0, 200.0), (200.0, 100.0), (300.0, 100.0), (300.0, 0.0)],
        [(5.0, 5.0), (5.0, 195.0), (195.0, 195.0), (195.0, 95.0), (295.0, 95.0), (295.0, 5.0)])


def test_calc_floorplan_areas_die_polygon_counterclockwise():
    schema = ASICAreaConstraint()
    # The same L shape wound the other way, the core must still be inside it.
    schema.set_diearea([(0, 0), (300, 0), (300, 100), (200, 100), (200, 200), (0, 200)])
    schema.set_coremargin(5.0)

    _, corearea = schema.calc_floorplan_areas()
    assert corearea == [
        (5.0, 5.0), (295.0, 5.0), (295.0, 95.0), (195.0, 95.0), (195.0, 195.0), (5.0, 195.0)]


def test_calc_floorplan_areas_die_polygon_closed():
    schema = ASICAreaConstraint()
    # A repeated first vertex closes the outline, the core is closed the same way.
    schema.set_diearea([(0, 0), (0, 100), (100, 100), (100, 0), (0, 0)])
    schema.set_coremargin(10.0)

    _, corearea = schema.calc_floorplan_areas()
    assert corearea == [
        (10.0, 10.0), (10.0, 90.0), (90.0, 90.0), (90.0, 10.0), (10.0, 10.0)]


def test_calc_floorplan_areas_die_polygon_collinear_vertex():
    schema = ASICAreaConstraint()
    # (50, 0) adds no shape, so it drops out of the offset outline.
    schema.set_diearea([(0, 0), (0, 100), (100, 100), (100, 0), (50, 0)])
    schema.set_coremargin(10.0)

    _, corearea = schema.calc_floorplan_areas()
    assert corearea == [(10.0, 10.0), (10.0, 90.0), (90.0, 90.0), (90.0, 10.0)]


def test_calc_floorplan_areas_die_polygon_diagonal():
    schema = ASICAreaConstraint()
    schema.set_diearea([(0, 0), (0, 100), (100, 0)])
    schema.set_coremargin(5.0)

    _, corearea = schema.calc_floorplan_areas()
    # The diagonal edge is mitered, so its corners sit back by 5 * (1 + sqrt(2)).
    miter = 100.0 - 5.0 * (1 + math.sqrt(2))
    assert corearea == [
        pytest.approx((5.0, 5.0)),
        pytest.approx((5.0, miter)),
        pytest.approx((miter, 5.0))]


def test_calc_floorplan_areas_die_polygon_margin_too_large():
    schema = ASICAreaConstraint()
    schema.set_diearea([(0, 0), (0, 200), (200, 200), (200, 100), (300, 100), (300, 0)])
    schema.set_coremargin(200.0)

    with pytest.raises(ValueError,
                       match=r"^core margin does not fit in the die area: "
                             r"offset is too large for the outline$"):
        schema.calc_floorplan_areas()


def test_calc_floorplan_areas_core_polygon_with_margin():
    schema = ASICAreaConstraint()
    schema.set_corearea([(10, 10), (10, 210), (210, 210), (210, 110), (310, 110), (310, 10)])
    schema.set_coremargin(5.0)

    diearea, corearea = schema.calc_floorplan_areas()
    # The die grows around the core and keeps the same outline. Growing it shrinks
    # the notch, so the reflex corner moves to (215, 115) rather than (215, 105).
    assert diearea == [
        (5.0, 5.0), (5.0, 215.0), (215.0, 215.0), (215.0, 115.0), (315.0, 115.0), (315.0, 5.0)]
    assert corearea == [
        (10.0, 10.0), (10.0, 210.0), (210.0, 210.0), (210.0, 110.0), (310.0, 110.0), (310.0, 10.0)]


def test_calc_floorplan_areas_core_at_origin_with_margin():
    schema = ASICAreaConstraint()
    schema.set_corearea([(0.0, 10.0), (100.0, 110.0)])
    schema.set_coremargin(5.0)

    # Growing the die would put it at x = -5, which OpenROAD rejects.
    with pytest.raises(ValueError,
                       match=r"^core margin places the die area at a negative x coordinate$"):
        schema.calc_floorplan_areas()


def test_calc_floorplan_areas_core_below_origin_with_margin():
    schema = ASICAreaConstraint()
    schema.set_corearea([(10.0, 0.0), (110.0, 100.0)])
    schema.set_coremargin(5.0)

    with pytest.raises(ValueError,
                       match=r"^core margin places the die area at a negative y coordinate$"):
        schema.calc_floorplan_areas()


def test_calc_floorplan_areas_core_with_margin():
    schema = ASICAreaConstraint()
    schema.set_corearea([(10.0, 10.0), (110.0, 60.0)])
    schema.set_coremargin(5.0)

    # The core coordinates are preserved so component placements stay valid.
    assert schema.calc_floorplan_areas() == (
        [(5.0, 5.0), (115.0, 65.0)],
        [(10.0, 10.0), (110.0, 60.0)])


def test_calc_floorplan_areas_core_without_margin():
    schema = ASICAreaConstraint()
    schema.set_corearea([(0.0, 0.0), (100.0, 100.0)])

    assert schema.calc_floorplan_areas() == (
        [(0.0, 0.0), (100.0, 100.0)],
        [(0.0, 0.0), (100.0, 100.0)])


def test_calc_floorplan_areas_margin_exceeds_die_width():
    schema = ASICAreaConstraint()
    schema.set_diearea_rectangle(500.0, 100.0)
    schema.set_coremargin(50.0)

    with pytest.raises(ValueError,
                       match=r"^core margin is greater than or equal to the die width$"):
        schema.calc_floorplan_areas()


def test_calc_floorplan_areas_margin_exceeds_die_height():
    schema = ASICAreaConstraint()
    schema.set_diearea_rectangle(100.0, 500.0)
    schema.set_coremargin(50.0)

    with pytest.raises(ValueError,
                       match=r"^core margin is greater than or equal to the die height$"):
        schema.calc_floorplan_areas()


def test_calc_floorplan_areas_step_index():
    schema = ASICAreaConstraint()
    schema.set_coremargin(1.0)
    schema.set_diearea_rectangle(500.0, 500.0, step="step0", index="0")

    assert schema.calc_floorplan_areas() is None
    assert schema.calc_floorplan_areas(step="step0", index="0") == (
        [(0.0, 0.0), (500.0, 500.0)],
        [(1.0, 1.0), (499.0, 499.0)])
