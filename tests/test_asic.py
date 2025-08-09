import logging
import pytest

from unittest.mock import patch

from siliconcompiler import ASICProject

from siliconcompiler import StdCellLibrarySchema, PDKSchema
from siliconcompiler.metrics import ASICMetricsSchema
from siliconcompiler.constraints import ASICTimingConstraintSchema, \
    ASICPinConstraints, ASICAreaConstraint, ASICComponentConstraints


def test_keys():
    assert ASICProject().getkeys() == (
        'arg',
        'asic',
        'checklist',
        'constraint',
        'flowgraph',
        'history',
        'library',
        'metric',
        'option',
        'record',
        'schemaversion',
        'tool')


def test_keys_asic():
    assert ASICProject().getkeys("asic") == (
        'asiclib',
        'delaymodel',
        'mainlib',
        'maxlayer',
        'minlayer',
        'pdk')


def test_keys_constraint():
    assert ASICProject().getkeys("constraint") == (
        'area',
        'component',
        'pin',
        'timing'
    )


def test_metrics():
    assert isinstance(ASICProject().get("metric", field="schema"), ASICMetricsSchema)


def test_getdict_type():
    assert ASICProject._getdict_type() == "ASICProject"


@pytest.mark.parametrize("type", [1, None])
def test_set_mainlib_invalid(type):
    with pytest.raises(TypeError,
                       match="main library must be string or standard cell library object"):
        ASICProject().set_mainlib(type)


def test_set_mainlib_string():
    proj = ASICProject()

    assert proj.get("asic", "mainlib") is None
    proj.set_mainlib("mainlib")
    assert proj.get("asic", "mainlib") == "mainlib"


def test_set_mainlib_obj():
    lib = StdCellLibrarySchema("thislib")
    proj = ASICProject()

    assert proj.get("asic", "mainlib") is None
    proj.set_mainlib(lib)
    assert proj.get("asic", "mainlib") == "thislib"
    assert proj.get("library", "thislib", field="schema") is lib


@pytest.mark.parametrize("type", [1, None])
def test_set_pdk_invalid(type):
    with pytest.raises(TypeError,
                       match="pdk must be string or PDK object"):
        ASICProject().set_pdk(type)


def test_set_pdk_string():
    proj = ASICProject()

    assert proj.get("asic", "pdk") is None
    proj.set_pdk("thispdk")
    assert proj.get("asic", "pdk") == "thispdk"


def test_set_pdk_obj():
    pdk = PDKSchema("thispdk")
    proj = ASICProject()

    assert proj.get("asic", "pdk") is None
    proj.set_pdk(pdk)
    assert proj.get("asic", "pdk") == "thispdk"
    assert proj.get("library", "thispdk", field="schema") is pdk


@pytest.mark.parametrize("type", [1, None])
def test_add_asiclib_invalid(type):
    with pytest.raises(TypeError,
                       match="asic library must be string or standard cell library object"):
        ASICProject().add_asiclib(type)


def test_add_asiclib_string():
    proj = ASICProject()

    assert proj.get("asic", "asiclib") == []
    proj.add_asiclib("thislib")
    assert proj.get("asic", "asiclib") == ["thislib"]


def test_add_asiclib_obj():
    lib = StdCellLibrarySchema("thislib")
    proj = ASICProject()

    assert proj.get("asic", "asiclib") == []
    proj.add_asiclib(lib)
    assert proj.get("asic", "asiclib") == ["thislib"]
    assert proj.get("library", "thislib", field="schema") is lib


def test_add_asiclib_list():
    proj = ASICProject()

    assert proj.get("asic", "asiclib") == []
    proj.add_asiclib(["lib0", "lib1"])
    assert proj.get("asic", "asiclib") == ["lib0", "lib1"]


def test_add_asiclib_list_clobber():
    proj = ASICProject()

    assert proj.get("asic", "asiclib") == []
    proj.add_asiclib(["lib0", "lib1"])
    assert proj.get("asic", "asiclib") == ["lib0", "lib1"]
    proj.add_asiclib(["lib3", "lib2"], clobber=True)
    assert proj.get("asic", "asiclib") == ["lib3", "lib2"]


def test_add_asiclib_clobber():
    proj = ASICProject()

    assert proj.get("asic", "asiclib") == []
    proj.add_asiclib(["lib0", "lib1"])
    assert proj.get("asic", "asiclib") == ["lib0", "lib1"]
    proj.add_asiclib("lib2", clobber=True)
    assert proj.get("asic", "asiclib") == ["lib2"]


def test_get_timingconstraints():
    proj = ASICProject()
    assert isinstance(proj.get_timingconstraints(), ASICTimingConstraintSchema)
    assert proj.get("constraint", "timing", field="schema") is proj.get_timingconstraints()


def test_get_pinconstraints():
    proj = ASICProject()
    assert isinstance(proj.get_pinconstraints(), ASICPinConstraints)
    assert proj.get("constraint", "pin", field="schema") is proj.get_pinconstraints()


def test_get_componentconstraints():
    proj = ASICProject()
    assert isinstance(proj.get_componentconstraints(), ASICComponentConstraints)
    assert proj.get("constraint", "component", field="schema") is proj.get_componentconstraints()


def test_get_areaconstraints():
    proj = ASICProject()
    assert isinstance(proj.get_areaconstraints(), ASICAreaConstraint)
    assert proj.get("constraint", "area", field="schema") is proj.get_areaconstraints()


def test_set_asic_routinglayers():
    proj = ASICProject()
    proj.set_asic_routinglayers("M1", "M5")
    assert proj.get("asic", "minlayer") == "M1"
    assert proj.get("asic", "maxlayer") == "M5"


def test_set_asic_delaymodel():
    proj = ASICProject()
    proj.set_asic_delaymodel("ccs")
    assert proj.get("asic", "delaymodel") == "ccs"


def test_add_dep_list():
    lib0 = StdCellLibrarySchema("thislib")
    lib1 = StdCellLibrarySchema("thatlib")
    proj = ASICProject()

    proj.add_dep([lib0, lib1])
    assert proj.get("library", "thislib", field="schema") is lib0
    assert proj.get("library", "thatlib", field="schema") is lib1


def test_add_dep_handoff():
    proj = ASICProject()

    with patch("siliconcompiler.Project.add_dep") as add_dep:
        proj.add_dep(None)
        add_dep.assert_called_once_with(None)


def test_check_manifest_empty(caplog):
    proj = ASICProject()
    setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    with patch("siliconcompiler.Project.check_manifest") as check_manifest:
        check_manifest.return_value = True
        assert proj.check_manifest() is False

    assert "[asic,pdk] has not been set" in caplog.text
    assert "[asic,mainlib] has not been set, this will be inferred" in caplog.text
    assert "[asic,asiclib] does not contain any libraries" in caplog.text
    assert "[asic,delaymodel] has not been set" in caplog.text


def test_check_manifest_missing_pdk(caplog):
    proj = ASICProject()
    setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    proj.set("asic", "pdk", "thispdk")

    with patch("siliconcompiler.Project.check_manifest") as check_manifest:
        check_manifest.return_value = True
        assert proj.check_manifest() is False

    assert "thispdk library has not been loaded" in caplog.text
    assert "[asic,mainlib] has not been set, this will be inferred" in caplog.text
    assert "[asic,asiclib] does not contain any libraries" in caplog.text
    assert "[asic,delaymodel] has not been set" in caplog.text


def test_check_manifest_incorrect_type_pdk(caplog):
    proj = ASICProject()
    setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    proj.add_dep(StdCellLibrarySchema("thislib"))
    proj.set("asic", "pdk", "thislib")

    with patch("siliconcompiler.Project.check_manifest") as check_manifest:
        check_manifest.return_value = True
        assert proj.check_manifest() is False

    assert "thislib must be a PDK" in caplog.text
    assert "[asic,mainlib] has not been set, this will be inferred" in caplog.text
    assert "[asic,asiclib] does not contain any libraries" in caplog.text
    assert "[asic,delaymodel] has not been set" in caplog.text


def test_check_manifest_main_libmissing(caplog):
    proj = ASICProject()
    setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    proj.set_pdk(PDKSchema("thispdk"))
    proj.set("asic", "mainlib", "thislib")

    with patch("siliconcompiler.Project.check_manifest") as check_manifest:
        check_manifest.return_value = True
        assert proj.check_manifest() is False

    assert "thislib library has not been loaded" in caplog.text
    assert "[asic,asiclib] does not contain any libraries" in caplog.text
    assert "thislib library must be added to [asic,asiclib]" in caplog.text
    assert "[asic,delaymodel] has not been set" in caplog.text


def test_check_manifest_asiclib_missing(caplog):
    proj = ASICProject()
    setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    proj.set_pdk(PDKSchema("thispdk"))
    proj.set("asic", "asiclib", "thislib")

    with patch("siliconcompiler.Project.check_manifest") as check_manifest:
        check_manifest.return_value = True
        assert proj.check_manifest() is False

    assert "[asic,mainlib] has not been set, this will be inferred" in caplog.text
    assert "thislib library has not been loaded" in caplog.text
    assert "[asic,delaymodel] has not been set" in caplog.text


def test_check_manifest_pass(caplog):
    proj = ASICProject()
    setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    proj.set_pdk(PDKSchema("thispdk"))
    proj.set_mainlib(StdCellLibrarySchema("thislib"))
    proj.add_asiclib("thislib")
    proj.set_asic_delaymodel("nldm")

    with patch("siliconcompiler.Project.check_manifest") as check_manifest:
        check_manifest.return_value = True
        assert proj.check_manifest() is True

    assert caplog.text == ""


def test_check_manifest_pass_missing_mainlib(caplog):
    proj = ASICProject()
    setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    proj.set_pdk(PDKSchema("thispdk"))
    proj.add_asiclib(StdCellLibrarySchema("thislib"))
    proj.set_asic_delaymodel("nldm")

    with patch("siliconcompiler.Project.check_manifest") as check_manifest:
        check_manifest.return_value = True
        assert proj.check_manifest() is True

    assert "[asic,mainlib] has not been set, this will be inferred" in caplog.text


def test_init_run_set_mainlib(caplog):
    proj = ASICProject()
    setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    proj.set_pdk(PDKSchema("thispdk"))
    proj.add_asiclib(StdCellLibrarySchema("thislib"))

    assert proj.get("asic", "mainlib") is None
    proj._init_run()
    assert proj.get("asic", "mainlib") == "thislib"

    assert "Setting main library to: thislib" in caplog.text


def test_init_run_set_pdk_asiclib(caplog):
    proj = ASICProject()
    setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    lib = StdCellLibrarySchema("thislib")
    lib.add_asic_pdk(PDKSchema("thispdk"))

    proj.set_mainlib(lib)

    assert proj.get("asic", "asiclib") == []
    assert proj.get("asic", "pdk") is None
    proj._init_run()
    assert proj.get("asic", "pdk") == "thispdk"
    assert proj.get("asic", "asiclib") == ["thislib"]

    assert "Setting pdk to: thispdk" in caplog.text
    assert "Adding thislib to [asic,asiclib]" in caplog.text


def test_init_run_handling_missing_lib(caplog):
    proj = ASICProject()
    setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    proj.set_mainlib("thislib")

    assert proj.get("asic", "asiclib") == []
    assert proj.get("asic", "pdk") is None
    proj._init_run()
    assert proj.get("asic", "pdk") is None
    assert proj.get("asic", "asiclib") == ["thislib"]

    assert "Adding thislib to [asic,asiclib]" in caplog.text


def test_summary_headers():
    proj = ASICProject()
    setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    proj.set_pdk("thispdk")
    proj.set_mainlib("thislib")
    proj.add_asiclib(["thislib", "thatlib"])

    with patch("siliconcompiler.Project._summary_headers") as parent:
        parent.return_value = [("parent", "stuff")]
        assert proj._summary_headers() == [
            ("parent", "stuff"),
            ('pdk', 'thispdk'),
            ('mainlib', 'thislib'),
            ('asiclib', 'thislib, thatlib')
        ]
        parent.assert_called_once()
