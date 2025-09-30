import logging
import pytest

from unittest.mock import patch

from siliconcompiler import FPGADevice, FPGAProject
from siliconcompiler.metrics import FPGAMetricsSchema
from siliconcompiler.constraints import FPGAComponentConstraints, \
    FPGAPinConstraints, FPGATimingConstraintSchema
from siliconcompiler.fpga import FPGAConstraint


def test_set_add():
    schema = FPGADevice("testfpga")
    assert schema.name == "testfpga"


def test_fpga_keys():
    assert FPGADevice().allkeys("fpga") == {
        ('lutsize',),
        ('partname',)
    }


def test_keys():
    assert FPGADevice().getkeys() == (
        'dataroot',
        'fileset',
        'fpga',
        'package'
    )


def test_getdict_type():
    assert FPGADevice._getdict_type() == "FPGADevice"


def test_set_partname():
    schema = FPGADevice()
    assert schema.get("fpga", "partname") is None
    schema.set_partname("fpga123")
    assert schema.get("fpga", "partname") == "fpga123"


def test_set_lutsize():
    schema = FPGADevice()
    assert schema.get("fpga", "lutsize") is None
    schema.set_lutsize(6)
    assert schema.get("fpga", "lutsize") == 6


def test_project_keys():
    assert FPGAProject().getkeys() == (
        'arg',
        'checklist',
        'constraint',
        'flowgraph',
        'fpga',
        'history',
        'library',
        'metric',
        'option',
        'record',
        'schemaversion',
        'tool')


def test_project_keys_fpga():
    assert FPGAProject().getkeys("fpga") == ('device',)


def test_project_keys_constraint():
    assert isinstance(FPGAProject().get("constraint", field="schema"), FPGAConstraint)
    assert FPGAProject().getkeys("constraint") == (
        'component',
        'pin',
        'timing'
    )


def test_project_metrics():
    assert isinstance(FPGAProject().get("metric", field="schema"), FPGAMetricsSchema)


def test_project_getdict_type():
    assert FPGAProject._getdict_type() == "FPGAProject"


def test_project_constraint():
    proj = FPGAProject()
    assert isinstance(proj.constraint, FPGAConstraint)
    assert proj.get("constraint", field="schema") is proj.constraint


def test_project_add_dep_list():
    fpga0 = FPGADevice("thisfpga")
    fpga1 = FPGADevice("thatfpga")
    proj = FPGAProject()

    proj.add_dep([fpga0, fpga1])
    assert proj.get("library", "thisfpga", field="schema") is fpga0
    assert proj.get("library", "thatfpga", field="schema") is fpga1


def test_project_add_dep_handoff():
    proj = FPGAProject()

    with patch("siliconcompiler.Project.add_dep") as add_dep:
        proj.add_dep(None)
        add_dep.assert_called_once_with(None)


def test_project_check_manifest_empty(monkeypatch, caplog):
    proj = FPGAProject()
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    with patch("siliconcompiler.Project.check_manifest") as check_manifest:
        check_manifest.return_value = True
        assert proj.check_manifest() is False

    assert "[fpga,device] has not been set." in caplog.text


def test_project_check_manifest_missing_fpga(monkeypatch, caplog):
    proj = FPGAProject()
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    proj.set_fpga("thisfpga")

    with patch("siliconcompiler.Project.check_manifest") as check_manifest:
        check_manifest.return_value = True
        assert proj.check_manifest() is False

    assert "FPGA library 'thisfpga' has not been loaded." in caplog.text


def test_project_check_manifest_pass(monkeypatch, caplog):
    proj = FPGAProject()
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    proj.set_fpga(FPGADevice("thisfpga"))

    with patch("siliconcompiler.Project.check_manifest") as check_manifest:
        check_manifest.return_value = True
        assert proj.check_manifest() is True

    assert caplog.text == ""


def test_project_summary_headers():
    proj = FPGAProject()

    proj.set_fpga("thisfpga")

    with patch("siliconcompiler.Project._summary_headers") as parent:
        parent.return_value = [("parent", "stuff")]
        assert proj._summary_headers() == [
            ("parent", "stuff"),
            ('fpga', 'thisfpga')
        ]
        parent.assert_called_once()


@pytest.mark.parametrize("type", [1, None])
def test_project_set_fpga_invalid(type):
    with pytest.raises(TypeError,
                       match="fpga must be an FPGADevice object or a string."):
        FPGAProject().set_fpga(type)


def test_project_set_fpga_string():
    proj = FPGAProject()

    assert proj.get("fpga", "device") is None
    proj.set_fpga("thisfpga")
    assert proj.get("fpga", "device") == "thisfpga"


def test_project_set_fpga_obj():
    fpga = FPGADevice("thisfpga")
    proj = FPGAProject()

    assert proj.get("fpga", "device") is None
    proj.set_fpga(fpga)
    assert proj.get("fpga", "device") == "thisfpga"
    assert proj.get("library", "thisfpga", field="schema") is fpga


def test_constraint_timing():
    const = FPGAConstraint()
    assert isinstance(const.timing, FPGATimingConstraintSchema)
    assert const.get("timing", field="schema") is const.timing


def test_constraint_pin():
    const = FPGAConstraint()
    assert isinstance(const.pin, FPGAPinConstraints)
    assert const.get("pin", field="schema") is const.pin


def test_constraint_component():
    const = FPGAConstraint()
    assert isinstance(const.component, FPGAComponentConstraints)
    assert const.get("component", field="schema") is const.component
