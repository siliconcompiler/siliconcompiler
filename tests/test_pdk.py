from unittest.mock import patch

from siliconcompiler.pdk import PDKSchema


def test_set_add():
    schema = PDKSchema("testpdk")
    assert schema.name == "testpdk"


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
