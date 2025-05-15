import pytest

from siliconcompiler.metric import MetricSchema


def test_clear():
    schema = MetricSchema()

    assert schema.set("errors", 5, step="teststep", index="testindex")
    assert schema.get("errors", step="teststep", index="testindex") == 5

    assert schema.set("warnings", 7, step="teststep", index="testindex")
    assert schema.get("warnings", step="teststep", index="testindex") == 7

    assert schema.set("tasktime", 12.5, step="teststep", index="testindex")
    assert schema.get("tasktime", step="teststep", index="testindex") == 12.5

    assert schema.set("totaltime", 15.5, step="teststep", index="testindex")
    assert schema.get("totaltime", step="teststep", index="testindex") == 15.5

    schema.clear("teststep", "testindex0")

    assert schema.get("errors", step="teststep", index="testindex") == 5
    assert schema.get("warnings", step="teststep", index="testindex") == 7
    assert schema.get("tasktime", step="teststep", index="testindex") == 12.5
    assert schema.get("totaltime", step="teststep", index="testindex") == 15.5

    schema.clear("teststep", "testindex")

    assert schema.get("errors", step="teststep", index="testindex") is None
    assert schema.get("warnings", step="teststep", index="testindex") is None
    assert schema.get("tasktime", step="teststep", index="testindex") is None
    assert schema.get("totaltime", step="teststep", index="testindex") is None


def test_record_no_unit():
    schema = MetricSchema()
    assert schema.record("teststep", "testindex", "errors", 5)
    assert schema.get("errors", step="teststep", index="testindex") == 5


def test_record_unit():
    schema = MetricSchema()
    assert schema.record("teststep", "testindex", "exetime", 5, unit='s')
    assert schema.get("exetime", step="teststep", index="testindex") == 5.0


def test_record_unit_covert():
    schema = MetricSchema()
    assert schema.record("teststep", "testindex", "exetime", 5, unit='ms')
    assert schema.get("exetime", step="teststep", index="testindex") == 0.005


def test_record_unit_mismatch():
    schema = MetricSchema()
    with pytest.raises(ValueError,
                       match="errors does not have a unit, but ms was supplied"):
        schema.record("teststep", "testindex", "errors", 5, unit='ms')
