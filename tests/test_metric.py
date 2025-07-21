import pytest

from datetime import datetime, timezone
from unittest.mock import patch

from siliconcompiler import MetricSchema
from siliconcompiler import RecordSchema, FlowgraphSchema
from siliconcompiler.record import RecordTime


def test_keys():
    assert MetricSchema().allkeys() == set([
        ('exetime',),
        ('tasktime',),
        ('memory',),
        ('warnings',),
        ('totaltime',),
        ('errors',),
    ])


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


def test_record_tasktime_no_data():
    schema = MetricSchema()
    assert schema.record_tasktime("testtwo", "0", RecordSchema()) is False
    assert schema.get("tasktime", step="testtwo", index="0") is None


def test_record_tasktime():
    record = RecordSchema()
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 0, 0, tzinfo=timezone.utc)
        record.record_time("testone", "0", RecordTime.START)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 0, 10, tzinfo=timezone.utc)
        record.record_time("testone", "0", RecordTime.END)

    schema = MetricSchema()
    assert schema.record_tasktime("testone", "0", record)
    assert schema.get("tasktime", step="testone", index="0") == 10.0


def test_record_totaltime_no_data():
    flow = FlowgraphSchema("testflow")
    flow.node("testone", "builtin.nop", index="0")
    flow.node("testone", "builtin.nop", index="1")
    flow.node("testone", "builtin.nop", index="2")
    flow.node("testtwo", "builtin.nop", index="0")
    flow.edge("testone", "testtwo", tail_index="0")
    flow.edge("testone", "testtwo", tail_index="1")
    flow.edge("testone", "testtwo", tail_index="2")

    record = RecordSchema()

    schema = MetricSchema()
    assert schema.record_totaltime("testone", "0", flow, record) is False
    assert schema.get("totaltime", step="testone", index="0") is None
    assert schema.record_totaltime("testone", "1", flow, record) is False
    assert schema.get("totaltime", step="testone", index="1") is None
    assert schema.record_totaltime("testone", "2", flow, record) is False
    assert schema.get("totaltime", step="testone", index="2") is None

    assert schema.record_totaltime("testtwo", "0", flow, record) is False
    assert schema.get("totaltime", step="testtwo", index="0") is None


def test_record_totaltime_linear():
    flow = FlowgraphSchema("testflow")
    flow.node("testone", "builtin.nop", index="0")
    flow.node("testone", "builtin.nop", index="1")
    flow.node("testone", "builtin.nop", index="2")
    flow.node("testtwo", "builtin.nop", index="0")
    flow.edge("testone", "testtwo", tail_index="0")
    flow.edge("testone", "testtwo", tail_index="1")
    flow.edge("testone", "testtwo", tail_index="2")

    record = RecordSchema()
    record.set("inputnode",
               [("testone", "0"), ("testone", "1"), ("testone", "2")],
               step="testtwo", index="0")

    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 0, 0, tzinfo=timezone.utc)
        record.record_time("testone", "0", RecordTime.START)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 0, 10, tzinfo=timezone.utc)
        record.record_time("testone", "0", RecordTime.END)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 0, 15, tzinfo=timezone.utc)
        record.record_time("testone", "1", RecordTime.START)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 0, 30, tzinfo=timezone.utc)
        record.record_time("testone", "1", RecordTime.END)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 0, 30, tzinfo=timezone.utc)
        record.record_time("testone", "2", RecordTime.START)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 0, 50, tzinfo=timezone.utc)
        record.record_time("testone", "2", RecordTime.END)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 1, 0, tzinfo=timezone.utc)
        record.record_time("testtwo", "0", RecordTime.START)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 1, 5, tzinfo=timezone.utc)
        record.record_time("testtwo", "0", RecordTime.END)

    schema = MetricSchema()
    assert schema.record_totaltime("testone", "0", flow, record)
    assert schema.get("totaltime", step="testone", index="0") == 10.0
    assert schema.record_totaltime("testone", "1", flow, record)
    assert schema.get("totaltime", step="testone", index="1") == 25.0
    assert schema.record_totaltime("testone", "2", flow, record)
    assert schema.get("totaltime", step="testone", index="2") == 45.0

    assert schema.record_totaltime("testtwo", "0", flow, record)
    assert schema.get("totaltime", step="testtwo", index="0") == 50.0


def test_record_totaltime_overlap():
    flow = FlowgraphSchema("testflow")
    flow.node("testone", "builtin.nop", index="0")
    flow.node("testone", "builtin.nop", index="1")
    flow.node("testone", "builtin.nop", index="2")
    flow.node("testtwo", "builtin.nop", index="0")
    flow.edge("testone", "testtwo", tail_index="0")
    flow.edge("testone", "testtwo", tail_index="1")
    flow.edge("testone", "testtwo", tail_index="2")

    record = RecordSchema()
    record.set("inputnode",
               [("testone", "0"), ("testone", "1"), ("testone", "2")],
               step="testtwo", index="0")

    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 0, 0, tzinfo=timezone.utc)
        record.record_time("testone", "0", RecordTime.START)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 0, 10, tzinfo=timezone.utc)
        record.record_time("testone", "0", RecordTime.END)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 0, 0, tzinfo=timezone.utc)
        record.record_time("testone", "1", RecordTime.START)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 0, 30, tzinfo=timezone.utc)
        record.record_time("testone", "1", RecordTime.END)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 0, 0, tzinfo=timezone.utc)
        record.record_time("testone", "2", RecordTime.START)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 0, 50, tzinfo=timezone.utc)
        record.record_time("testone", "2", RecordTime.END)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 1, 0, tzinfo=timezone.utc)
        record.record_time("testtwo", "0", RecordTime.START)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 1, 5, tzinfo=timezone.utc)
        record.record_time("testtwo", "0", RecordTime.END)

    schema = MetricSchema()
    assert schema.record_totaltime("testone", "0", flow, record)
    assert schema.get("totaltime", step="testone", index="0") == 10.0
    assert schema.record_totaltime("testone", "1", flow, record)
    assert schema.get("totaltime", step="testone", index="1") == 30.0
    assert schema.record_totaltime("testone", "2", flow, record)
    assert schema.get("totaltime", step="testone", index="2") == 50.0

    assert schema.record_totaltime("testtwo", "0", flow, record)
    assert schema.get("totaltime", step="testtwo", index="0") == 55.0


def test_record_totaltime_overlap_staggered():
    flow = FlowgraphSchema("testflow")
    flow.node("testone", "builtin.nop", index="0")
    flow.node("testone", "builtin.nop", index="1")
    flow.node("testone", "builtin.nop", index="2")
    flow.node("testtwo", "builtin.nop", index="0")
    flow.edge("testone", "testtwo", tail_index="0")
    flow.edge("testone", "testtwo", tail_index="1")
    flow.edge("testone", "testtwo", tail_index="2")

    record = RecordSchema()
    record.set("inputnode",
               [("testone", "0"), ("testone", "1"), ("testone", "2")],
               step="testtwo", index="0")

    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 0, 0, tzinfo=timezone.utc)
        record.record_time("testone", "0", RecordTime.START)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 0, 10, tzinfo=timezone.utc)
        record.record_time("testone", "0", RecordTime.END)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 0, 5, tzinfo=timezone.utc)
        record.record_time("testone", "1", RecordTime.START)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 0, 30, tzinfo=timezone.utc)
        record.record_time("testone", "1", RecordTime.END)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 0, 10, tzinfo=timezone.utc)
        record.record_time("testone", "2", RecordTime.START)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 0, 50, tzinfo=timezone.utc)
        record.record_time("testone", "2", RecordTime.END)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 1, 0, tzinfo=timezone.utc)
        record.record_time("testtwo", "0", RecordTime.START)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 1, 5, tzinfo=timezone.utc)
        record.record_time("testtwo", "0", RecordTime.END)

    schema = MetricSchema()
    assert schema.record_totaltime("testone", "0", flow, record)
    assert schema.get("totaltime", step="testone", index="0") == 10.0
    assert schema.record_totaltime("testone", "1", flow, record)
    assert schema.get("totaltime", step="testone", index="1") == 30.0
    assert schema.record_totaltime("testone", "2", flow, record)
    assert schema.get("totaltime", step="testone", index="2") == 50.0

    assert schema.record_totaltime("testtwo", "0", flow, record)
    assert schema.get("totaltime", step="testtwo", index="0") == 55.0


def test_record_totaltime_overlap_staggered_with_gap():
    flow = FlowgraphSchema("testflow")
    flow.node("testone", "builtin.nop", index="0")
    flow.node("testone", "builtin.nop", index="1")
    flow.node("testone", "builtin.nop", index="2")
    flow.node("testtwo", "builtin.nop", index="0")
    flow.edge("testone", "testtwo", tail_index="0")
    flow.edge("testone", "testtwo", tail_index="1")
    flow.edge("testone", "testtwo", tail_index="2")

    record = RecordSchema()
    record.set("inputnode",
               [("testone", "0"), ("testone", "1"), ("testone", "2")],
               step="testtwo", index="0")

    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 0, 0, tzinfo=timezone.utc)
        record.record_time("testone", "0", RecordTime.START)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 0, 10, tzinfo=timezone.utc)
        record.record_time("testone", "0", RecordTime.END)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 0, 5, tzinfo=timezone.utc)
        record.record_time("testone", "1", RecordTime.START)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 0, 30, tzinfo=timezone.utc)
        record.record_time("testone", "1", RecordTime.END)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 0, 31, tzinfo=timezone.utc)
        record.record_time("testone", "2", RecordTime.START)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 0, 50, tzinfo=timezone.utc)
        record.record_time("testone", "2", RecordTime.END)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 1, 0, tzinfo=timezone.utc)
        record.record_time("testtwo", "0", RecordTime.START)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 1, 5, tzinfo=timezone.utc)
        record.record_time("testtwo", "0", RecordTime.END)

    schema = MetricSchema()
    assert schema.record_totaltime("testone", "0", flow, record)
    assert schema.get("totaltime", step="testone", index="0") == 10.0
    assert schema.record_totaltime("testone", "1", flow, record)
    assert schema.get("totaltime", step="testone", index="1") == 30.0
    assert schema.record_totaltime("testone", "2", flow, record)
    assert schema.get("totaltime", step="testone", index="2") == 49.0

    assert schema.record_totaltime("testtwo", "0", flow, record)
    assert schema.get("totaltime", step="testtwo", index="0") == 54.0


def test_record_totaltime_overlap_staggered_with_all_contained():
    flow = FlowgraphSchema("testflow")
    flow.node("testone", "builtin.nop", index="0")
    flow.node("testone", "builtin.nop", index="1")
    flow.node("testone", "builtin.nop", index="2")
    flow.node("testtwo", "builtin.nop", index="0")
    flow.edge("testone", "testtwo", tail_index="0")
    flow.edge("testone", "testtwo", tail_index="1")
    flow.edge("testone", "testtwo", tail_index="2")

    record = RecordSchema()
    record.set("inputnode",
               [("testone", "0"), ("testone", "1"), ("testone", "2")],
               step="testtwo", index="0")

    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 0, 0, tzinfo=timezone.utc)
        record.record_time("testone", "0", RecordTime.START)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 0, 10, tzinfo=timezone.utc)
        record.record_time("testone", "0", RecordTime.END)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 0, 1, tzinfo=timezone.utc)
        record.record_time("testone", "1", RecordTime.START)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 0, 2, tzinfo=timezone.utc)
        record.record_time("testone", "1", RecordTime.END)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 0, 3, tzinfo=timezone.utc)
        record.record_time("testone", "2", RecordTime.START)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 0, 4, tzinfo=timezone.utc)
        record.record_time("testone", "2", RecordTime.END)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 1, 0, tzinfo=timezone.utc)
        record.record_time("testtwo", "0", RecordTime.START)
    with patch("siliconcompiler.record.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2020, 3, 11, 14, 1, 5, tzinfo=timezone.utc)
        record.record_time("testtwo", "0", RecordTime.END)

    schema = MetricSchema()
    assert schema.record_totaltime("testone", "0", flow, record)
    assert schema.get("totaltime", step="testone", index="0") == 10.0
    assert schema.record_totaltime("testone", "1", flow, record)
    assert schema.get("totaltime", step="testone", index="1") == 2.0
    assert schema.record_totaltime("testone", "2", flow, record)
    assert schema.get("totaltime", step="testone", index="2") == 4.0

    assert schema.record_totaltime("testtwo", "0", flow, record)
    assert schema.get("totaltime", step="testtwo", index="0") == 15.0
