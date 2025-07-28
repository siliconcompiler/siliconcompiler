import pytest

from datetime import datetime, timezone
from unittest.mock import patch

from siliconcompiler import MetricSchema
from siliconcompiler import RecordSchema, FlowgraphSchema
from siliconcompiler.record import RecordTime
from siliconcompiler.schema import PerNode, Scope


def test_keys():
    assert MetricSchema().allkeys() == set([
        ('exetime',),
        ('tasktime',),
        ('memory',),
        ('warnings',),
        ('totaltime',),
        ('errors',),
    ])


@pytest.mark.parametrize("key", MetricSchema().allkeys())
def test_key_params(key):
    param = MetricSchema().get(*key, field=None)
    assert param.get(field="pernode") == PerNode.REQUIRED
    assert param.get(field="scope") == Scope.JOB


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


def test_summary_table_all_nodes():
    schema = MetricSchema()

    assert schema.set("tasktime", 5, step="step", index="0")
    assert schema.set("tasktime", 7, step="step", index="1")
    assert schema.set("tasktime", 12.5, step="step", index="2")
    assert schema.set("tasktime", 15.5, step="step", index="3")

    table = schema.summary_table()
    assert table.index.to_list() == ["tasktime"]
    assert table.columns.to_list() == ["unit", "step/0", "step/1", "step/2", "step/3"]
    assert table.to_dict() == {
        'unit': {
            'tasktime': 's'
        },
        'step/0': {
            'tasktime': '05.000'
        },
        'step/1': {
            'tasktime': '07.000'
        },
        'step/2': {
            'tasktime': '12.500'
        },
        'step/3': {
            'tasktime': '15.500'
        }
    }


def test_summary_table_select_nodes():
    schema = MetricSchema()

    assert schema.set("tasktime", 5, step="step", index="0")
    assert schema.set("tasktime", 7, step="step", index="1")
    assert schema.set("tasktime", 12.5, step="step", index="2")
    assert schema.set("tasktime", 15.5, step="step", index="3")

    table = schema.summary_table(nodes=[("step", "1"), ("step", "3")])
    assert table.index.to_list() == ["tasktime"]
    assert table.columns.to_list() == ["unit", "step/1", "step/3"]
    assert table.to_dict() == {
        'unit': {
            'tasktime': 's'
        },
        'step/1': {
            'tasktime': '07.000'
        },
        'step/3': {
            'tasktime': '15.500'
        }
    }


def test_summary_table_raw():
    schema = MetricSchema()

    assert schema.set("tasktime", 5, step="step", index="0")
    assert schema.set("tasktime", 7, step="step", index="1")
    assert schema.set("tasktime", 12.5, step="step", index="2")
    assert schema.set("tasktime", 15.5, step="step", index="3")

    table = schema.summary_table(formatted=False)
    assert table.index.to_list() == ["tasktime"]
    assert table.columns.to_list() == ["unit", "step/0", "step/1", "step/2", "step/3"]
    assert table.to_dict() == {
        'unit': {
            'tasktime': 's'
        },
        'step/0': {
            'tasktime': 5.000
        },
        'step/1': {
            'tasktime': 7.000
        },
        'step/2': {
            'tasktime': 12.500
        },
        'step/3': {
            'tasktime': 15.500
        }
    }


def test_summary_table_multiple_metrics():
    schema = MetricSchema()

    assert schema.set("tasktime", 5, step="step", index="0")
    assert schema.set("tasktime", 7, step="step", index="1")
    assert schema.set("tasktime", 12.5, step="step", index="2")
    assert schema.set("tasktime", 15.5, step="step", index="3")

    assert schema.set("exetime", 15, step="step", index="0")
    assert schema.set("exetime", 17, step="step", index="1")
    assert schema.set("exetime", 112.5, step="step", index="2")
    assert schema.set("exetime", 115.5, step="step", index="3")

    table = schema.summary_table()
    assert table.index.to_list() == ["exetime", "tasktime"]
    assert table.columns.to_list() == ["unit", "step/0", "step/1", "step/2", "step/3"]
    assert table.to_dict() == {
        'unit': {
            'tasktime': 's',
            'exetime': 's'
        },
        'step/0': {
            'tasktime': '05.000',
            'exetime': '15.000'
        },
        'step/1': {
            'tasktime': '07.000',
            'exetime': '17.000'
        },
        'step/2': {
            'tasktime': '12.500',
            'exetime': '01:52.500'
        },
        'step/3': {
            'tasktime': '15.500',
            'exetime': '01:55.500'
        }
    }


def test_summary_table_no_trim():
    schema = MetricSchema()

    assert schema.set("tasktime", 5, step="step", index="0")
    assert schema.set("tasktime", 7, step="step", index="1")
    assert schema.set("tasktime", 12.5, step="step", index="2")
    assert schema.set("tasktime", 15.5, step="step", index="3")

    assert schema.set("exetime", 15, step="step", index="0")
    assert schema.set("exetime", 17, step="step", index="1")
    assert schema.set("exetime", 112.5, step="step", index="2")
    assert schema.set("exetime", 115.5, step="step", index="3")

    table = schema.summary_table(trim_empty_metrics=False)
    assert table.index.to_list() == [
        'errors', 'exetime', 'memory', 'tasktime', 'totaltime', 'warnings']
    assert table.columns.to_list() == ["unit", "step/0", "step/1", "step/2", "step/3"]
    assert table.to_dict() == {
        'unit': {
            'errors': '',
            'exetime': 's',
            'memory': 'B',
            'tasktime': 's',
            'totaltime': 's',
            'warnings': ''
        },
        'step/0': {
            'errors': ' ---  ',
            'exetime': '15.000',
            'memory': ' ---  ',
            'tasktime': '05.000',
            'totaltime': ' ---  ',
            'warnings': ' ---  '
        },
        'step/1': {
            'errors': ' ---  ',
            'exetime': '17.000',
            'memory': ' ---  ',
            'tasktime': '07.000',
            'totaltime': ' ---  ',
            'warnings': ' ---  '
        },
        'step/2': {
            'errors': ' ---  ',
            'exetime': '01:52.500',
            'memory': ' ---  ',
            'tasktime': '12.500',
            'totaltime': ' ---  ',
            'warnings': ' ---  '
        },
        'step/3': {
            'errors': ' ---  ',
            'exetime': '01:55.500',
            'memory': ' ---  ',
            'tasktime': '15.500',
            'totaltime': ' ---  ',
            'warnings': ' ---  '
        }
    }


def test_summary(capsys):
    schema = MetricSchema()

    assert schema.set("tasktime", 5, step="step", index="0")
    assert schema.set("tasktime", 7, step="step", index="1")
    assert schema.set("tasktime", 12.5, step="step", index="2")
    assert schema.set("tasktime", 15.5, step="step", index="3")

    schema.summary(headers=[("pdk", "asap7"), ("library", "asap7_library")])

    out = capsys.readouterr().out
    assert out.splitlines() == [
        '----------------------------------------------------------------------------',
        'SUMMARY :',
        'pdk     : asap7',
        'library : asap7_library',
        '',
        '         unit  step/0  step/1  step/2  step/3',
        'tasktime    s  05.000  07.000  12.500  15.500',
        '----------------------------------------------------------------------------']


def test_summary_empty(capsys):
    schema = MetricSchema()

    schema.summary(headers=[("pdk", "asap7"), ("library", "asap7_library")])

    out = capsys.readouterr().out
    assert out.splitlines() == [
        '----------------------------------------------------------------------------',
        'SUMMARY :',
        'pdk     : asap7',
        'library : asap7_library',
        '',
        '  No metrics to display!',
        '----------------------------------------------------------------------------']


def test_summary_column_width(capsys):
    schema = MetricSchema()

    assert schema.set("tasktime", 5, step="step", index="0")
    assert schema.set("tasktime", 7, step="step", index="1")
    assert schema.set("tasktime", 12.5, step="step", index="2")
    assert schema.set("tasktime", 15.5, step="step", index="3")

    schema.summary(headers=[("pdk", "asap7"), ("library", "asap7_library")], column_width=5)

    out = capsys.readouterr().out
    assert out.splitlines() == [
        '----------------------------------------------------------------------------',
        'SUMMARY :',
        'pdk     : asap7',
        'library : asap7_library',
        '',
        '         unit   s...0   s...1   s...2   s...3',
        'tasktime    s  05.000  07.000  12.500  15.500',
        '----------------------------------------------------------------------------']
