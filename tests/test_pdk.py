import pytest

from unittest.mock import patch

from siliconcompiler import PDKSchema


def test_set_add():
    schema = PDKSchema("testpdk")
    assert schema.name == "testpdk"


def test_asic_keys():
    assert PDKSchema().allkeys("pdk") == {
        ('scribe',),
        ('pexmodelfileset', 'default', 'default'),
        ('displayfileset', 'default'),
        ('drc', 'waiverfileset', 'default', 'default'),
        ('drc', 'runsetfileset', 'default', 'default'),
        ('edgemargin',),
        ('lvs', 'runsetfileset', 'default', 'default'),
        ('unitcost',),
        ('maxlayer',),
        ('layermapfileset', 'default', 'default', 'default'),
        ('devmodelfileset', 'default', 'default'),
        ('lvs', 'waiverfileset', 'default', 'default'),
        ('wafersize',),
        ('node',),
        ('minlayer',),
        ('fill', 'runsetfileset', 'default', 'default'),
        ('foundry',),
        ('aprtechfileset', 'default'),
        ('fill', 'waiverfileset', 'default', 'default'),
        ('d0',),
        ('erc', 'waiverfileset', 'default', 'default'),
        ('erc', 'runsetfileset', 'default', 'default'),
        ('stackup',)
    }


def test_keys():
    assert PDKSchema().getkeys() == (
        'dataroot',
        'fileset',
        'package',
        'pdk'
    )


def test_getdict_type():
    assert PDKSchema._getdict_type() == "PDKSchema"


def test_set_foundry():
    schema = PDKSchema()
    assert schema.get("pdk", "foundry") is None
    schema.set_foundry("virtual")
    assert schema.get("pdk", "foundry") == "virtual"


def test_set_node():
    schema = PDKSchema()
    assert schema.get("pdk", "node") is None
    schema.set_node(12)
    assert schema.get("pdk", "node") == 12


def test_set_stackup():
    schema = PDKSchema()
    assert schema.get("pdk", "stackup") is None
    schema.set_stackup("10LM")
    assert schema.get("pdk", "stackup") == "10LM"


def test_set_wafersize():
    schema = PDKSchema()
    assert schema.get("pdk", "wafersize") is None
    schema.set_wafersize(200)
    assert schema.get("pdk", "wafersize") == 200


def test_set_unitcost():
    schema = PDKSchema()
    assert schema.get("pdk", "unitcost") is None
    schema.set_unitcost(1000)
    assert schema.get("pdk", "unitcost") == 1000


def test_set_defectdensity():
    schema = PDKSchema()
    assert schema.get("pdk", "d0") is None
    schema.set_defectdensity(0.1)
    assert schema.get("pdk", "d0") == 0.1


def test_set_scribewidth():
    schema = PDKSchema()
    assert schema.get("pdk", "scribe") is None
    schema.set_scribewidth(0.1, 0.1)
    assert schema.get("pdk", "scribe") == (0.1, 0.1)


def test_set_edgemargin():
    schema = PDKSchema()
    assert schema.get("pdk", "edgemargin") is None
    schema.set_edgemargin(1)
    assert schema.get("pdk", "edgemargin") == 1


def test_set_aprroutinglayers():
    schema = PDKSchema()
    assert schema.get("pdk", "minlayer") is None
    assert schema.get("pdk", "maxlayer") is None
    schema.set_aprroutinglayers("M1", "M5")
    assert schema.get("pdk", "minlayer") == "M1"
    assert schema.get("pdk", "maxlayer") == "M5"


def test_add_aprtechfileset():
    schema = PDKSchema()

    with patch("siliconcompiler.PDKSchema._assert_fileset") as fileset_assert:
        schema.add_aprtechfileset("testtool", "physical")
        fileset_assert.assert_called_once_with("physical")
        fileset_assert.reset_mock()

        assert schema.get("pdk", "aprtechfileset", "testtool") == ["physical"]

        schema.add_aprtechfileset("testtool", "layout", clobber=True)
        fileset_assert.assert_called_once_with("layout")
        assert schema.get("pdk", "aprtechfileset", "testtool") == ["layout"]


def test_add_aprtechfileset_with_fileset():
    schema = PDKSchema()

    with patch("siliconcompiler.PDKSchema._assert_fileset") as fileset_assert:
        with schema.active_fileset("physical"):
            schema.add_aprtechfileset("testtool")
        fileset_assert.assert_called_once_with("physical")
        assert schema.get("pdk", "aprtechfileset", "testtool") == ["physical"]


def test_add_displayfileset():
    schema = PDKSchema()

    with patch("siliconcompiler.PDKSchema._assert_fileset") as fileset_assert:
        schema.add_displayfileset("testtool", "physical")
        fileset_assert.assert_called_once_with("physical")
        fileset_assert.reset_mock()

        assert schema.get("pdk", "displayfileset", "testtool") == ["physical"]

        schema.add_displayfileset("testtool", "layout", clobber=True)
        fileset_assert.assert_called_once_with("layout")
        assert schema.get("pdk", "displayfileset", "testtool") == ["layout"]


def test_add_displayfileset_with_fileset():
    schema = PDKSchema()

    with patch("siliconcompiler.PDKSchema._assert_fileset") as fileset_assert:
        with schema.active_fileset("physical"):
            schema.add_displayfileset("testtool")
        fileset_assert.assert_called_once_with("physical")
        assert schema.get("pdk", "displayfileset", "testtool") == ["physical"]


def test_add_layermapfileset():
    schema = PDKSchema()

    with patch("siliconcompiler.PDKSchema._assert_fileset") as fileset_assert:
        schema.add_layermapfileset("testtool", "def", "oas", "physical")
        fileset_assert.assert_called_once_with("physical")
        fileset_assert.reset_mock()

        assert schema.get("pdk", "layermapfileset", "testtool", "def", "oas") == ["physical"]

        schema.add_layermapfileset("testtool", "def", "oas", "layout", clobber=True)
        fileset_assert.assert_called_once_with("layout")
        assert schema.get("pdk", "layermapfileset", "testtool", "def", "oas") == ["layout"]


def test_add_layermapfileset_with_fileset():
    schema = PDKSchema()

    with patch("siliconcompiler.PDKSchema._assert_fileset") as fileset_assert:
        with schema.active_fileset("physical"):
            schema.add_layermapfileset("testtool", "def", "oas")
        fileset_assert.assert_called_once_with("physical")
        assert schema.get("pdk", "layermapfileset", "testtool", "def", "oas") == ["physical"]


def test_add_devmodelfileset():
    schema = PDKSchema()

    with patch("siliconcompiler.PDKSchema._assert_fileset") as fileset_assert:
        schema.add_devmodelfileset("testtool", "spice", "model")
        fileset_assert.assert_called_once_with("model")
        fileset_assert.reset_mock()

        assert schema.get("pdk", "devmodelfileset", "testtool", "spice") == ["model"]

        schema.add_devmodelfileset("testtool", "spice", "model.spice", clobber=True)
        fileset_assert.assert_called_once_with("model.spice")
        assert schema.get("pdk", "devmodelfileset", "testtool", "spice") == ["model.spice"]


def test_add_devmodelfileset_with_fileset():
    schema = PDKSchema()

    with patch("siliconcompiler.PDKSchema._assert_fileset") as fileset_assert:
        with schema.active_fileset("model"):
            schema.add_devmodelfileset("testtool", "spice")
        fileset_assert.assert_called_once_with("model")
        assert schema.get("pdk", "devmodelfileset", "testtool", "spice") == ["model"]


def test_add_pexmodelfileset():
    schema = PDKSchema()

    with patch("siliconcompiler.PDKSchema._assert_fileset") as fileset_assert:
        schema.add_pexmodelfileset("testtool", "slow", "model")
        fileset_assert.assert_called_once_with("model")
        fileset_assert.reset_mock()

        assert schema.get("pdk", "pexmodelfileset", "testtool", "slow") == ["model"]

        schema.add_pexmodelfileset("testtool", "slow", "model.slow", clobber=True)
        fileset_assert.assert_called_once_with("model.slow")
        assert schema.get("pdk", "pexmodelfileset", "testtool", "slow") == ["model.slow"]


def test_add_pexmodelfileset_with_fileset():
    schema = PDKSchema()

    with patch("siliconcompiler.PDKSchema._assert_fileset") as fileset_assert:
        with schema.active_fileset("model"):
            schema.add_pexmodelfileset("testtool", "slow")
        fileset_assert.assert_called_once_with("model")
        assert schema.get("pdk", "pexmodelfileset", "testtool", "slow") == ["model"]


def test_add_runsetfileset():
    schema = PDKSchema()

    with patch("siliconcompiler.PDKSchema._assert_fileset") as fileset_assert:
        schema.add_runsetfileset("drc", "testtool", "drc.feol", "feol")
        fileset_assert.assert_called_once_with("feol")
        fileset_assert.reset_mock()

        assert schema.get("pdk", "drc", "runsetfileset", "testtool", "drc.feol") == ["feol"]

        schema.add_runsetfileset("drc", "testtool", "drc.feol", "drc.feol", clobber=True)
        fileset_assert.assert_called_once_with("drc.feol")
        assert schema.get("pdk", "drc", "runsetfileset", "testtool", "drc.feol") == ["drc.feol"]


def test_add_runsetfileset_with_fileset():
    schema = PDKSchema()

    with patch("siliconcompiler.PDKSchema._assert_fileset") as fileset_assert:
        with schema.active_fileset("beol"):
            schema.add_runsetfileset("drc", "testtool", "drc.beol")
        fileset_assert.assert_called_once_with("beol")
        assert schema.get("pdk", "drc", "runsetfileset", "testtool", "drc.beol") == ["beol"]


def test_add_waiverfileset():
    schema = PDKSchema()

    with patch("siliconcompiler.PDKSchema._assert_fileset") as fileset_assert:
        schema.add_waiverfileset("drc", "testtool", "drc.feol", "feol")
        fileset_assert.assert_called_once_with("feol")
        fileset_assert.reset_mock()

        assert schema.get("pdk", "drc", "waiverfileset", "testtool", "drc.feol") == ["feol"]

        schema.add_waiverfileset("drc", "testtool", "drc.feol", "drc.feol", clobber=True)
        fileset_assert.assert_called_once_with("drc.feol")
        assert schema.get("pdk", "drc", "waiverfileset", "testtool", "drc.feol") == ["drc.feol"]


def test_add_waiverfileset_with_fileset():
    schema = PDKSchema()

    with patch("siliconcompiler.PDKSchema._assert_fileset") as fileset_assert:
        with schema.active_fileset("beol"):
            schema.add_waiverfileset("drc", "testtool", "drc.beol")
        fileset_assert.assert_called_once_with("beol")
        assert schema.get("pdk", "drc", "waiverfileset", "testtool", "drc.beol") == ["beol"]


@pytest.mark.parametrize("d0,area,expect", [
    (1.25, 150000*75000, 0.245),
    (1.25, 75000*75000, 0.495),
    (1.25, 5000*5000, 0.996),
    (1.25, 1000*1000, 0.999),
    (5.00, 150000*75000, 0.003),
    (5.00, 75000*75000, 0.060),
    (5.00, 5000*5000, 0.987),
    (5.00, 1000*1000, 0.999),
])
def test_calc_yield_poisson(d0, area, expect):
    pdk = PDKSchema()
    pdk.set("pdk", "d0", d0)

    assert int(1000 * pdk.calc_yield(area)) == int(1000 * expect)


@pytest.mark.parametrize("d0,area,expect", [
    (1.25, 150000*75000, 0.288),
    (1.25, 75000*75000, 0.515),
    (1.25, 5000*5000, 0.996),
    (1.25, 1000*1000, 0.999),
    (5.00, 150000*75000, 0.031),
    (5.00, 75000*75000, 0.111),
    (5.00, 5000*5000, 0.987),
    (5.00, 1000*1000, 0.999),
    (0.00, 500, 1.0)
])
def test_calc_yield_murphy(d0, area, expect):
    pdk = PDKSchema()
    pdk.set("pdk", "d0", d0)

    assert int(1000 * pdk.calc_yield(area, model="murphy")) == int(1000 * expect)


def test_calc_yield_no_d0():
    with pytest.raises(ValueError, match=r"\[pdk,d0\] has not been set"):
        PDKSchema().calc_yield(1.0)


def test_calc_yield_wrong_model():
    pdk = PDKSchema()
    pdk.set("pdk", "d0", 1.0)

    with pytest.raises(ValueError, match="Unknown yield model: unknown"):
        pdk.calc_yield(1.0, model="unknown")


@pytest.mark.parametrize("wafer,edge,scribe,die,expect", [
    (300, 2, (0.1, 0.1), (150000, 75000), 0),
    (300, 2, (0.1, 0.1), (75000, 75000), 4),
    (300, 2, (0.1, 0.1), (5000, 5000), 2520),
    (300, 2, (0.1, 0.1), (2000, 2000), 15332),
    (200, 2, (0.1, 0.1), (2000, 2000), 6656),
    (2, 2, (0.1, 0.1), (2000, 2000), 0),
    (200, 2, (0.0, 0.0), (0, 0), 0),
    (200, None, None, (2000, 2000), 7628),
])
def test_calc_dpw(wafer, edge, scribe, die, expect):
    pdk = PDKSchema()
    pdk.set("pdk", "wafersize", wafer)
    if edge:
        pdk.set("pdk", "edgemargin", edge)
    if scribe:
        pdk.set("pdk", "scribe", scribe)

    assert pdk.calc_dpw(die[0], die[1]) == expect


def test_calc_dpw_no_wafer():
    with pytest.raises(ValueError, match=r"\[pdk,wafersize\] has not been set"):
        PDKSchema().calc_dpw(1.0, 1.0)
