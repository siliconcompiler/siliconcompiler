import pytest
import logging

import os.path

from unittest.mock import patch

from siliconcompiler import Flowgraph
from siliconcompiler import NodeStatus
from siliconcompiler.schema_support.record import RecordSchema
from siliconcompiler.flowgraph import RuntimeFlowgraph
from siliconcompiler.schema import BaseSchema
from siliconcompiler.tools.builtin.nop import NOPTask
from siliconcompiler.tools.builtin.join import JoinTask


@pytest.fixture
def large_flow():
    flow = Flowgraph("testflow")

    flow.node("joinone", "siliconcompiler.tools.builtin.join/JoinTask")
    for n in range(3):
        flow.node("stepone", "siliconcompiler.tools.builtin.nop/NOPTask", index=n)
        flow.edge("stepone", "joinone", tail_index=n)

    flow.node("jointwo", "siliconcompiler.tools.builtin.join/JoinTask")
    for n in range(3):
        flow.node("steptwo", "siliconcompiler.tools.builtin.nop/NOPTask", index=n)

        flow.edge("joinone", "steptwo", head_index=n)
        flow.edge("steptwo", "jointwo", tail_index=n)

    flow.node("jointhree", "siliconcompiler.tools.builtin.join/JoinTask")
    for n in range(3):
        flow.node("stepthree", "siliconcompiler.tools.builtin.nop/NOPTask", index=n)

        flow.edge("jointwo", "stepthree", head_index=n)
        flow.edge("stepthree", "jointhree", tail_index=n)

    return flow


def test_init():
    flow = Flowgraph("testflow")
    assert flow.name == "testflow"


def test_node():
    flow = Flowgraph("testflow")
    flow.node("teststep", NOPTask())

    assert flow.get("teststep", "0", "tool") == "builtin"
    assert flow.get("teststep", "0", "task") == "nop"
    assert flow.get("teststep", "0", "taskmodule") == "siliconcompiler.tools.builtin.nop/NOPTask"


def test_node_class():
    flow = Flowgraph("testflow")
    flow.node("teststep", NOPTask)

    assert flow.get("teststep", "0", "tool") == "builtin"
    assert flow.get("teststep", "0", "task") == "nop"
    assert flow.get("teststep", "0", "taskmodule") == "siliconcompiler.tools.builtin.nop/NOPTask"


def test_node_str():
    flow = Flowgraph("testflow")
    flow.node("teststep", "siliconcompiler.tools.builtin.nop/NOPTask")

    assert flow.get("teststep", "0", "tool") == "builtin"
    assert flow.get("teststep", "0", "task") == "nop"
    assert flow.get("teststep", "0", "taskmodule") == "siliconcompiler.tools.builtin.nop/NOPTask"


def test_node_invalid_task():
    flow = Flowgraph("testflow")

    with pytest.raises(ValueError, match=r"^12 is not a string or module and cannot be used to "
                                         r"setup a task\.$"):
        flow.node("teststep", 12)


def test_node_step_name():
    flow = Flowgraph("testflow")

    # Valid step
    flow.node("teststep", NOPTask())

    # Invalid step
    with pytest.raises(ValueError, match="^teststep/ is not a valid step, it cannot contain '/'$"):
        flow.node("teststep/", NOPTask())


def test_node_index_name():
    flow = Flowgraph("testflow")

    # Valid index
    flow.node("teststep", NOPTask(), index="index")

    # Invalid index
    with pytest.raises(ValueError, match="^index/ is not a valid index, it cannot contain '/'$"):
        flow.node("teststep", NOPTask(), index="index/")


def test_node_index():
    flow = Flowgraph("testflow")
    flow.node("teststep", "siliconcompiler.tools.builtin.nop/NOPTask", index=1)

    assert flow.get("teststep", "0", "tool") is None
    assert flow.get("teststep", "0", "task") is None
    assert flow.get("teststep", "0", "taskmodule") is None

    assert flow.get("teststep", "1", "tool") == "builtin"
    assert flow.get("teststep", "1", "task") == "nop"
    assert flow.get("teststep", "1", "taskmodule") == "siliconcompiler.tools.builtin.nop/NOPTask"


@pytest.mark.parametrize("step", ["global", "default",
                                  "sc_collected_files", "sc_config", "sc_blah"])
def test_node_reserved_step(step):
    flow = Flowgraph("testflow")

    with pytest.raises(ValueError, match=f"^{step} is a reserved name$"):
        flow.node(step, "siliconcompiler.tools.builtin.nop/NOPTask")


def test_node_allow_step():
    Flowgraph("testflow").node("scblah", "siliconcompiler.tools.builtin.nop/NOPTask")


@pytest.mark.parametrize("index", ["global", "default"])
def test_node_reserved_index(index):
    flow = Flowgraph("testflow")

    with pytest.raises(ValueError, match=f"^{index} is a reserved name$"):
        flow.node("teststep", "siliconcompiler.tools.builtin.nop/NOPTask", index=index)


def test_edge():
    flow = Flowgraph("testflow")
    flow.node("stepone", "siliconcompiler.tools.builtin.nop/NOPTask")
    flow.node("steptwo", "siliconcompiler.tools.builtin.nop/NOPTask")

    flow.edge("stepone", "steptwo")

    assert flow.get("steptwo", "0", "input") == [("stepone", "0")]


def test_edge_double():
    flow = Flowgraph("testflow")
    flow.node("stepone", "siliconcompiler.tools.builtin.nop/NOPTask")
    flow.node("steptwo", "siliconcompiler.tools.builtin.nop/NOPTask")

    flow.edge("stepone", "steptwo")
    flow.edge("stepone", "steptwo")

    assert flow.get("steptwo", "0", "input") == [("stepone", "0")]


def test_edge_multiple_inputs():
    flow = Flowgraph("testflow")
    flow.node("stepone", "siliconcompiler.tools.builtin.nop/NOPTask", index=0)
    flow.node("stepone", "siliconcompiler.tools.builtin.nop/NOPTask", index=1)
    flow.node("steptwo", "siliconcompiler.tools.builtin.nop/NOPTask", index=0)
    flow.node("steptwo", "siliconcompiler.tools.builtin.nop/NOPTask", index=1)

    flow.edge("stepone", "steptwo", tail_index=0)
    flow.edge("stepone", "steptwo", tail_index=1)

    assert flow.get("steptwo", "0", "input") == [("stepone", "0"), ("stepone", "1")]
    assert flow.get("steptwo", "1", "input") == []


def test_edge_multiple_outputs():
    flow = Flowgraph("testflow")
    flow.node("stepone", "siliconcompiler.tools.builtin.nop/NOPTask", index=0)
    flow.node("stepone", "siliconcompiler.tools.builtin.nop/NOPTask", index=1)
    flow.node("steptwo", "siliconcompiler.tools.builtin.nop/NOPTask", index=0)
    flow.node("steptwo", "siliconcompiler.tools.builtin.nop/NOPTask", index=1)

    flow.edge("stepone", "steptwo", head_index=0)
    flow.edge("stepone", "steptwo", head_index=1)

    assert flow.get("steptwo", "0", "input") == [("stepone", "0")]
    assert flow.get("steptwo", "1", "input") == [("stepone", "0")]


def test_edge_undefined():
    flow = Flowgraph("testflow")
    flow.node("stepone", "siliconcompiler.tools.builtin.nop/NOPTask")

    with pytest.raises(ValueError, match=r"^steptwo/0 is not a defined node in testflow\.$"):
        flow.edge("stepone", "steptwo")


def test_remove_node_one_index(large_flow):
    large_flow.remove_node("steptwo", "1")

    assert large_flow.getkeys("steptwo") == ("0", "2")
    assert large_flow.get("jointwo", "0", "input") == [
        ('joinone', '0'), ('steptwo', '0'), ('steptwo', '2')]


def test_remove_node_all_index(large_flow):
    large_flow.remove_node("steptwo")

    assert 'steptwo' not in large_flow.getkeys()
    assert large_flow.get("jointwo", "0", "input") == [('joinone', '0')]


def test_remove_node_no_step(large_flow):
    with pytest.raises(ValueError,
                       match='^invalidstep is not a valid step in testflow$'):
        large_flow.remove_node("invalidstep")


def test_remove_node_no_index(large_flow):
    with pytest.raises(ValueError,
                       match='^4 is not a valid index for steptwo in testflow$'):
        large_flow.remove_node('steptwo', 4)


def test_insert_node(large_flow):
    large_flow.insert_node(
        "newnode", "siliconcompiler.tools.builtin.nop/NOPTask", before_step="joinone"
    )

    assert ("newnode", "0") in large_flow.get_nodes()
    assert large_flow.get_execution_order() == (
        (('stepone', '0'), ('stepone', '1'), ('stepone', '2')),
        (('joinone', '0'),),
        (('newnode', '0'),),
        (('steptwo', '0'), ('steptwo', '1'), ('steptwo', '2')),
        (('jointwo', '0'),),
        (('stepthree', '0'), ('stepthree', '1'), ('stepthree', '2')),
        (('jointhree', '0'),))
    assert large_flow.get_node_outputs("joinone", "0") == (('newnode', '0'),)
    assert large_flow.get_node_outputs("newnode", "0") == \
        (('steptwo', '0'), ('steptwo', '1'), ('steptwo', '2'))


def test_insert_node_branch(large_flow):
    large_flow.insert_node(
        "newnode", "siliconcompiler.tools.builtin.nop/NOPTask",
        before_step="stepone",
        before_index=2
    )

    assert ("newnode", "0") in large_flow.get_nodes()
    assert large_flow.get_execution_order() == (
        (('stepone', '0'), ('stepone', '1'), ('stepone', '2')),
        (('newnode', '0'),),
        (('joinone', '0'),),
        (('steptwo', '0'), ('steptwo', '1'), ('steptwo', '2')),
        (('jointwo', '0'),),
        (('stepthree', '0'), ('stepthree', '1'), ('stepthree', '2')),
        (('jointhree', '0'),))
    assert large_flow.get_node_outputs("stepone", "0") == (('joinone', '0'),)
    assert large_flow.get_node_outputs("stepone", "1") == (('joinone', '0'),)
    assert large_flow.get_node_outputs("stepone", "2") == (('newnode', '0'),)
    assert large_flow.get_node_outputs("joinone", "0") == \
        (('steptwo', '0'), ('steptwo', '1'), ('steptwo', '2'))


def test_insert_node_invalid(large_flow):
    with pytest.raises(ValueError, match="^invalid/0 is not a valid node in testflow$"):
        large_flow.insert_node(
            "newnode", "siliconcompiler.tools.builtin.nop/NOPTask", before_step="invalid"
        )


def test_get_nodes(large_flow):
    assert large_flow.get_nodes() == (
        ('joinone', '0'), ('jointhree', '0'), ('jointwo', '0'),
        ('stepone', '0'), ('stepone', '1'), ('stepone', '2'),
        ('stepthree', '0'), ('stepthree', '1'), ('stepthree', '2'),
        ('steptwo', '0'), ('steptwo', '1'), ('steptwo', '2'))

    # check cache
    assert large_flow.get_nodes() is large_flow.get_nodes()


def test_get_nodes_cache_update(large_flow):
    assert large_flow.get_nodes() == (
        ('joinone', '0'), ('jointhree', '0'), ('jointwo', '0'),
        ('stepone', '0'), ('stepone', '1'), ('stepone', '2'),
        ('stepthree', '0'), ('stepthree', '1'), ('stepthree', '2'),
        ('steptwo', '0'), ('steptwo', '1'), ('steptwo', '2'))

    large_flow.node("testnode", NOPTask())

    assert large_flow.get_nodes() == (
        ('joinone', '0'), ('jointhree', '0'), ('jointwo', '0'),
        ('stepone', '0'), ('stepone', '1'), ('stepone', '2'),
        ('stepthree', '0'), ('stepthree', '1'), ('stepthree', '2'),
        ('steptwo', '0'), ('steptwo', '1'), ('steptwo', '2'),
        ('testnode', '0'))


def test_get_entry_nodes(large_flow):
    large_flow.node("testnode", NOPTask())

    assert large_flow.get_entry_nodes() == (('stepone', '0'), ('stepone', '1'), ('stepone', '2'),
                                            ('testnode', '0'))

    # check cache
    assert large_flow.get_entry_nodes() is large_flow.get_entry_nodes()


def test_get_exit_nodes(large_flow):
    large_flow.node("testnode", NOPTask())

    assert large_flow.get_exit_nodes() == (('jointhree', '0'), ('testnode', '0'))

    # check cache
    assert large_flow.get_exit_nodes() is large_flow.get_exit_nodes()


def test_get_execution_order_forward(large_flow):
    large_flow.node("testnode", NOPTask())

    assert large_flow.get_execution_order() == (
        (('stepone', '0'), ('stepone', '1'), ('stepone', '2'), ('testnode', '0')),
        (('joinone', '0'),),
        (('steptwo', '0'), ('steptwo', '1'), ('steptwo', '2')),
        (('jointwo', '0'),),
        (('stepthree', '0'), ('stepthree', '1'), ('stepthree', '2')),
        (('jointhree', '0'),))

    # check cache
    assert large_flow.get_execution_order() is large_flow.get_execution_order()
    assert large_flow.get_execution_order() is not large_flow.get_execution_order(reverse=True)


def test_get_execution_order_reverse(large_flow):
    large_flow.node("testnode", NOPTask())

    assert large_flow.get_execution_order(reverse=True) == (
        (('jointhree', '0'), ('testnode', '0')),
        (('stepthree', '0'), ('stepthree', '1'), ('stepthree', '2')),
        (('jointwo', '0'),),
        (('steptwo', '0'), ('steptwo', '1'), ('steptwo', '2')),
        (('joinone', '0'),),
        (('stepone', '0'), ('stepone', '1'), ('stepone', '2')))

    # check cache
    assert large_flow.get_execution_order(reverse=True) is \
        large_flow.get_execution_order(reverse=True)
    assert large_flow.get_execution_order(reverse=True) is not large_flow.get_execution_order()


def test_get_node_outputs(large_flow):
    large_flow.node("testnode", NOPTask())

    assert large_flow.get_node_outputs("testnode", "0") == tuple()
    assert large_flow.get_node_outputs("stepone", "0") == (("joinone", "0"),)
    assert large_flow.get_node_outputs("stepone", "1") == (("joinone", "0"),)
    assert large_flow.get_node_outputs("stepone", "2") == (("joinone", "0"),)
    assert large_flow.get_node_outputs("joinone", "0") == (
        ('steptwo', '0'), ('steptwo', '1'), ('steptwo', '2'))
    assert large_flow.get_node_outputs("steptwo", "0") == (("jointwo", "0"),)
    assert large_flow.get_node_outputs("steptwo", "1") == (("jointwo", "0"),)
    assert large_flow.get_node_outputs("steptwo", "2") == (("jointwo", "0"),)
    assert large_flow.get_node_outputs("jointwo", "0") == (
        ('stepthree', '0'), ('stepthree', '1'), ('stepthree', '2'))
    assert large_flow.get_node_outputs("stepthree", "0") == (("jointhree", "0"),)
    assert large_flow.get_node_outputs("stepthree", "1") == (("jointhree", "0"),)
    assert large_flow.get_node_outputs("stepthree", "2") == (("jointhree", "0"),)
    assert large_flow.get_node_outputs("jointhree", "0") == tuple()

    # check cache
    assert large_flow.get_node_outputs("testnode", "0") is \
        large_flow.get_node_outputs("testnode", "0")


def test_get_node_outputs_invalid(large_flow):
    with pytest.raises(ValueError, match="^testnode/0 is not a valid node$"):
        large_flow.get_node_outputs("testnode", "0")


def test_graph():
    rtl_flow = Flowgraph("rtl")
    rtl_flow.node("import", NOPTask())
    rtl_flow.node("syn", NOPTask())
    rtl_flow.node("export", NOPTask())
    rtl_flow.edge("import", "syn")
    rtl_flow.edge("syn", "export")

    apr_flow = Flowgraph("apr")
    apr_flow.node("floorplan", NOPTask())
    apr_flow.node("place", NOPTask())
    apr_flow.node("cts", NOPTask())
    apr_flow.node("route", NOPTask())
    apr_flow.edge("floorplan", "place")
    apr_flow.edge("place", "cts")
    apr_flow.edge("cts", "route")

    signoff_flow = Flowgraph("signoff")
    signoff_flow.node("extspice", NOPTask())
    signoff_flow.node("drc", NOPTask())
    signoff_flow.node("lvs", NOPTask())
    signoff_flow.edge("drc", "lvs")

    flow = Flowgraph("composite")
    flow.graph(rtl_flow, name="rtl")
    flow.graph(apr_flow, name="apr")
    flow.graph(signoff_flow, name="signoff")

    flow.edge("rtl.export", "apr.floorplan")
    flow.edge("apr.route", "signoff.extspice")
    flow.edge("apr.route", "signoff.drc")

    assert flow.get_execution_order() == (
        (('rtl.import', '0'),),
        (('rtl.syn', '0'),),
        (('rtl.export', '0'),),
        (('apr.floorplan', '0'),),
        (('apr.place', '0'),),
        (('apr.cts', '0'),),
        (('apr.route', '0'),),
        (('signoff.drc', '0'), ('signoff.extspice', '0')),
        (('signoff.lvs', '0'),))


def test_graph_no_names():
    rtl_flow = Flowgraph("rtl")
    rtl_flow.node("import", NOPTask())
    rtl_flow.node("syn", NOPTask())
    rtl_flow.node("export", NOPTask())
    rtl_flow.edge("import", "syn")
    rtl_flow.edge("syn", "export")

    apr_flow = Flowgraph("apr")
    apr_flow.node("floorplan", NOPTask())
    apr_flow.node("place", NOPTask())
    apr_flow.node("cts", NOPTask())
    apr_flow.node("route", NOPTask())
    apr_flow.edge("floorplan", "place")
    apr_flow.edge("place", "cts")
    apr_flow.edge("cts", "route")

    signoff_flow = Flowgraph("signoff")
    signoff_flow.node("extspice", NOPTask())
    signoff_flow.node("drc", NOPTask())
    signoff_flow.node("lvs", NOPTask())
    signoff_flow.edge("drc", "lvs")

    flow = Flowgraph("composite")
    flow.graph(rtl_flow)
    flow.graph(apr_flow)
    flow.graph(signoff_flow)

    flow.edge("export", "floorplan")
    flow.edge("route", "extspice")
    flow.edge("route", "drc")

    assert flow.get_execution_order() == (
        (('import', '0'),),
        (('syn', '0'),),
        (('export', '0'),),
        (('floorplan', '0'),),
        (('place', '0'),),
        (('cts', '0'),),
        (('route', '0'),),
        (('drc', '0'), ('extspice', '0')),
        (('lvs', '0'),))


def test_graph_overlapping_names():
    rtl_flow = Flowgraph("rtl")
    rtl_flow.node("import", NOPTask())

    apr_flow = Flowgraph("apr")
    apr_flow.node("import", NOPTask())

    flow = Flowgraph("composite")
    flow.graph(rtl_flow)

    with pytest.raises(ValueError, match="^import is already defined$"):
        flow.graph(apr_flow)


def test_graph_invalid_subgraph_type():
    rtl_flow = Flowgraph("rtl")
    rtl_flow.node("import", NOPTask())

    apr_flow = BaseSchema()

    flow = Flowgraph("composite")
    flow.graph(rtl_flow)

    with pytest.raises(ValueError,
                       match=r"^subflow must a Flowgraph, not: "
                             r"<class 'siliconcompiler\.schema\.baseschema\.BaseSchema'>$"):
        flow.graph(apr_flow)


def test_validate(large_flow):
    assert large_flow.validate()


def test_validate_duplicate_edge(large_flow, caplog):
    large_flow.add("joinone", "0", "input", ("stepone", "0"))
    assert not large_flow.validate(logger=logging.getLogger())
    assert "Duplicate edge from stepone/0 to joinone/0 in the testflow flowgraph" in caplog.text


def test_validate_missing_node(large_flow, caplog):
    large_flow.add("joinone", "0", "input", ("notvalid", "0"))
    assert not large_flow.validate(logger=logging.getLogger())
    assert "notvalid/0 is missing in the testflow flowgraph" in caplog.text


@pytest.mark.parametrize("item", ["tool", "task", "taskmodule"])
def test_validate_missing_config(large_flow, caplog, item):
    large_flow.unset("joinone", "0", item)
    assert not large_flow.validate(logger=logging.getLogger())
    assert f"joinone/0 is missing a {item} definition in the testflow flowgraph" in caplog.text


def test_validate_loop(large_flow, caplog):
    large_flow.add("stepone", "2", "input", ("jointwo", "0"))
    assert not large_flow.validate(logger=logging.getLogger())
    assert "stepone/0 -> joinone/0 -> steptwo/0 -> jointwo/0 -> stepone/2 -> joinone/0 forms " \
        "a loop in testflow" in caplog.text
    assert "stepone/1 -> joinone/0 -> steptwo/0 -> jointwo/0 -> stepone/2 -> joinone/0 forms " \
        "a loop in testflow" in caplog.text


def test_runtime_init():
    with pytest.raises(ValueError,
                       match=r"^base must a Flowgraph, not: "
                             r"<class 'siliconcompiler\.schema\.baseschema\.BaseSchema'>$"):
        RuntimeFlowgraph(BaseSchema())


def test_runtime_nodes_from():
    apr_flow = Flowgraph("apr")
    apr_flow.node("floorplan", NOPTask())
    apr_flow.node("place", NOPTask())
    apr_flow.node("cts", NOPTask())
    apr_flow.node("route", NOPTask())
    apr_flow.edge("floorplan", "place")
    apr_flow.edge("place", "cts")
    apr_flow.edge("cts", "route")

    runtime = RuntimeFlowgraph(apr_flow, from_steps=["place"])
    assert runtime.get_nodes() == (('cts', '0'), ('place', '0'), ('route', '0'))
    assert runtime.get_execution_order() == ((('place', '0'),), (('cts', '0'),), (('route', '0'),))


def test_runtime_nodes_to():
    apr_flow = Flowgraph("apr")
    apr_flow.node("floorplan", NOPTask())
    apr_flow.node("place", NOPTask())
    apr_flow.node("cts", NOPTask())
    apr_flow.node("route", NOPTask())
    apr_flow.edge("floorplan", "place")
    apr_flow.edge("place", "cts")
    apr_flow.edge("cts", "route")

    runtime = RuntimeFlowgraph(apr_flow, to_steps=["place"])
    assert runtime.get_nodes() == (('floorplan', '0'), ('place', '0'))
    assert runtime.get_execution_order() == ((('floorplan', '0'),), (('place', '0'),))


def test_runtime_nodes_from_to():
    apr_flow = Flowgraph("apr")
    apr_flow.node("floorplan", NOPTask())
    apr_flow.node("place", NOPTask())
    apr_flow.node("cts", NOPTask())
    apr_flow.node("route", NOPTask())
    apr_flow.edge("floorplan", "place")
    apr_flow.edge("place", "cts")
    apr_flow.edge("cts", "route")

    runtime = RuntimeFlowgraph(apr_flow, from_steps=["place"], to_steps=["cts"])
    assert runtime.get_nodes() == (('cts', '0'), ('place', '0'))
    assert runtime.get_execution_order() == ((('place', '0'),), (('cts', '0'),))


def test_runtime_get_nodes_args_none(large_flow):
    runtime = RuntimeFlowgraph(large_flow, args=(None, None))
    assert runtime.get_entry_nodes() == (('stepone', '0'), ('stepone', '1'), ('stepone', '2'))


def test_runtime_get_nodes_args(large_flow):
    runtime = RuntimeFlowgraph(large_flow, args=("stepone", "0"))
    assert runtime.get_nodes() == (('stepone', '0'),)


def test_runtime_get_entry_nodes_args(large_flow):
    runtime = RuntimeFlowgraph(large_flow, args=("stepone", "0"))
    assert runtime.get_entry_nodes() == (('stepone', '0'),)


def test_runtime_get_exit_nodes_args(large_flow):
    runtime = RuntimeFlowgraph(large_flow, args=("stepone", "0"))
    assert runtime.get_exit_nodes() == (('stepone', '0'),)


def test_runtime_get_nodes_args_just_step(large_flow):
    runtime = RuntimeFlowgraph(large_flow, args=("stepone", None))
    assert runtime.get_nodes() == (('stepone', '0'), ('stepone', '1'), ('stepone', '2'))


def test_runtime_get_entry_nodes_args_just_step(large_flow):
    runtime = RuntimeFlowgraph(large_flow, args=("stepone", None))
    assert runtime.get_entry_nodes() == (('stepone', '0'), ('stepone', '1'), ('stepone', '2'))


def test_runtime_get_exit_nodes_args_just_step(large_flow):
    runtime = RuntimeFlowgraph(large_flow, args=("stepone", None))
    assert runtime.get_exit_nodes() == (('stepone', '0'), ('stepone', '1'), ('stepone', '2'))


def test_runtime_nodes_prune(large_flow):
    runtime = RuntimeFlowgraph(large_flow, prune_nodes=[
        ("stepone", "0"), ("steptwo", "1"), ("stepthree", "2")])
    assert runtime.get_nodes() == (
        ('joinone', '0'), ('jointhree', '0'), ('jointwo', '0'),
        ('stepone', '1'), ('stepone', '2'),
        ('stepthree', '0'), ('stepthree', '1'),
        ('steptwo', '0'), ('steptwo', '2'))
    assert runtime.get_execution_order() == (
        (('stepone', '1'), ('stepone', '2')),
        (('joinone', '0'),),
        (('steptwo', '0'), ('steptwo', '2')),
        (('jointwo', '0'),),
        (('stepthree', '0'), ('stepthree', '1')),
        (('jointhree', '0'),))


def test_runtime_get_entry_nodes_prune_from(large_flow):
    runtime = RuntimeFlowgraph(large_flow, prune_nodes=[
        ("stepone", "0"), ("steptwo", "1"), ("stepthree", "2")])
    assert runtime.get_entry_nodes() == (('stepone', '1'), ('stepone', '2'))


def test_runtime_get_nodes_starting_at_invalid(large_flow):
    runtime = RuntimeFlowgraph(large_flow, prune_nodes=[
        ("stepone", "0"), ("steptwo", "1"), ("stepthree", "2")])
    with pytest.raises(ValueError, match="^stepone/0 is not a valid node$"):
        runtime.get_nodes_starting_at("stepone", "0")


def test_runtime_get_nodes_starting_at(large_flow):
    runtime = RuntimeFlowgraph(large_flow, prune_nodes=[
        ("stepone", "0"), ("steptwo", "1"), ("stepthree", "2")])
    assert runtime.get_nodes_starting_at("steptwo", "0") == (
        ('jointhree', '0'), ('jointwo', '0'),
        ('stepthree', '0'), ('stepthree', '1'),
        ('steptwo', '0'))


def test_runtime_get_entry_nodes(large_flow):
    runtime = RuntimeFlowgraph(large_flow, prune_nodes=[
        ("stepone", "0"), ("steptwo", "1"), ("stepthree", "2")])
    assert runtime.get_entry_nodes() == (('stepone', '1'), ('stepone', '2'))


def test_runtime_get_exit_nodes(large_flow):
    runtime = RuntimeFlowgraph(large_flow, prune_nodes=[
        ("stepone", "0"), ("steptwo", "1"), ("stepthree", "2")])
    assert runtime.get_exit_nodes() == (('jointhree', '0'),)


def test_runtime_get_entry_nodes_invalid_steps(large_flow):
    all_steps = ["step1"]
    runtime = RuntimeFlowgraph(large_flow, from_steps=all_steps, to_steps=all_steps)
    assert runtime.get_entry_nodes() == tuple()
    assert runtime.get_exit_nodes() == tuple()


def test_runtime_get_entry_nodes_jumbled_values(large_flow):
    all_steps = ["stepone", "joinone", "steptwo", "jointwo", "stepthree", "jointhree"]
    runtime = RuntimeFlowgraph(large_flow, from_steps=all_steps, to_steps=all_steps)
    assert runtime.get_entry_nodes() == (('stepone', '0'), ('stepone', '1'), ('stepone', '2'))


def test_runtime_get_exit_nodes_jumbled_values(large_flow):
    all_steps = ["stepone", "joinone", "steptwo", "jointwo", "stepthree", "jointhree"]
    runtime = RuntimeFlowgraph(large_flow, from_steps=all_steps, to_steps=all_steps)
    assert runtime.get_exit_nodes() == (('jointhree', '0'),)


def test_runtime_get_nodes_flows():
    '''
    A -- B -- C -- D
    |              |
    ----------------
    '''
    flow = Flowgraph('test')
    flow.node('A', JoinTask())

    flow.node('B', JoinTask())
    flow.edge('A', 'B')

    flow.node('C', JoinTask())
    flow.edge('B', 'C')

    flow.node('D', JoinTask())
    flow.edge('A', 'D')
    flow.edge('C', 'D')

    assert RuntimeFlowgraph(flow).get_nodes() == (
        ('A', '0'), ('B', '0'), ('C', '0'), ('D', '0'))


def test_runtime_get_nodes_flows_to():
    '''
    Check to ensure forked graph is handled properly with to
    A -- B -- C -- D
    |    |    |    |
    Aa  [Ba]  Ca   Da
    '''
    flow = Flowgraph('test')

    prev = None
    for n in ('A', 'B', 'C', 'D'):
        flow.node(n, NOPTask())
        flow.node(n + 'a', NOPTask())
        flow.edge(n, n + 'a')

        if prev:
            flow.edge(prev, n)

        prev = n

    assert RuntimeFlowgraph(flow, to_steps=["Ba"]).get_nodes() == (
        ('A', '0'),
        ('B', '0'),
        ('Ba', '0')
    )


def test_runtime_get_nodes_flows_to_multiple():
    '''
    Check to ensure forked graph is handled properly with to and multiple ends
    A -- B -- C -- D
    |    |    |    |
    Aa  [Ba]  Ca  [Da]
    '''
    flow = Flowgraph('test')

    prev = None
    for n in ('A', 'B', 'C', 'D'):
        flow.node(n, NOPTask())
        flow.node(n + 'a', NOPTask())
        flow.edge(n, n + 'a')

        if prev:
            flow.edge(prev, n)

        prev = n

    assert RuntimeFlowgraph(flow, to_steps=["Ba", "Da"]).get_nodes() == (
        ('A', '0'),
        ('B', '0'),
        ('Ba', '0'),
        ('C', '0'),
        ('D', '0'),
        ('Da', '0')
    )


def test_runtime_get_nodes_flows_from():
    '''
    Check to ensure forked graph is handled properly with from
    A --{B}-- C -- D
    |    |    |    |
    Aa   Ba   Ca   Da
    '''
    flow = Flowgraph('test')

    prev = None
    for n in ('A', 'B', 'C', 'D'):
        flow.node(n, NOPTask())
        flow.node(n + 'a', NOPTask())
        flow.edge(n, n + 'a')

        if prev:
            flow.edge(prev, n)

        prev = n

    assert RuntimeFlowgraph(flow, from_steps=["B"]).get_nodes() == (
        ('B', '0'),
        ('Ba', '0'),
        ('C', '0'),
        ('Ca', '0'),
        ('D', '0'),
        ('Da', '0')
    )


def test_runtime_get_nodes_flows_from_to():
    '''
    Check to ensure forked graph is handled properly with from/to
    A --{B}-- C -- D
    |    |    |    |
    Aa   Ba  [Ca]  Da
    '''
    flow = Flowgraph('test')

    prev = None
    for n in ('A', 'B', 'C', 'D'):
        flow.node(n, NOPTask())
        flow.node(n + 'a', NOPTask())
        flow.edge(n, n + 'a')

        if prev:
            flow.edge(prev, n)

        prev = n

    assert RuntimeFlowgraph(flow, from_steps=["B"], to_steps=["Ca"]).get_nodes() == (
        ('B', '0'),
        ('C', '0'),
        ('Ca', '0')
    )


def test_runtime_get_nodes_flows_disjoint_graph_from():
    '''
    Check to ensure get_nodes properly handles disjoint flowgraphs
    A --{B}-- C -- D

    E -- F -- G -- H
    '''
    flow = Flowgraph('test')

    prev = None
    for n in ('A', 'B', 'C', 'D'):
        flow.node(n, NOPTask())

        if prev:
            flow.edge(prev, n)

        prev = n

    prev = None
    for n in ('E', 'F', 'G', 'H'):
        flow.node(n, NOPTask())

        if prev:
            flow.edge(prev, n)

        prev = n

    assert RuntimeFlowgraph(flow, from_steps=["B"]).get_nodes() == (
        ('B', '0'),
        ('C', '0'),
        ('D', '0')
    )


def test_runtime_get_nodes_flows_disjoint_graph_to():
    '''
    Check to ensure get_nodes properly handles disjoint flowgraphs
    A -- B --[C]-- D

    E -- F -- G -- H
    '''
    flow = Flowgraph('test')

    prev = None
    for n in ('A', 'B', 'C', 'D'):
        flow.node(n, NOPTask())

        if prev:
            flow.edge(prev, n)

        prev = n

    prev = None
    for n in ('E', 'F', 'G', 'H'):
        flow.node(n, NOPTask())

        if prev:
            flow.edge(prev, n)

        prev = n

    assert RuntimeFlowgraph(flow, to_steps=["C"]).get_nodes() == (
        ('A', '0'),
        ('B', '0'),
        ('C', '0')
    )


def test_runtime_get_nodes_flows_disjoint_graph_from_to():
    '''
    Check to ensure get_nodes properly handles disjoint flowgraphs
    A --{B}--[C]-- D

    E -- F -- G -- H
    '''
    flow = Flowgraph('test')

    prev = None
    for n in ('A', 'B', 'C', 'D'):
        flow.node(n, NOPTask())

        if prev:
            flow.edge(prev, n)

        prev = n

    prev = None
    for n in ('E', 'F', 'G', 'H'):
        flow.node(n, NOPTask())

        if prev:
            flow.edge(prev, n)

        prev = n

    assert RuntimeFlowgraph(flow, from_steps=["B"], to_steps=["C"]).get_nodes() == (
        ('B', '0'),
        ('C', '0')
    )


def test_runtime_get_nodes_flows_cut_middle():
    '''
    Check to ensure get_nodes properly handles pruning the middle node
    {A} -- {X} --C -- [D]
    '''
    flow = Flowgraph('test')

    prev = None
    for n in ('A', 'B', 'C', 'D'):
        flow.node(n, NOPTask())

        if prev:
            flow.edge(prev, n)

        prev = n

    assert RuntimeFlowgraph(flow, prune_nodes=[("B", "0")]).get_nodes() == tuple()


def test_get_node_inputs_no_record(large_flow):
    runtime = RuntimeFlowgraph(large_flow, prune_nodes=[
        ("stepone", "0"), ("steptwo", "1"), ("stepthree", "2")])
    assert runtime.get_node_inputs("stepone", "1") == []
    assert runtime.get_node_inputs("joinone", "0") == [('stepone', '1'), ('stepone', '2')]
    assert runtime.get_node_inputs("steptwo", "0") == [('joinone', '0')]


def test_get_node_inputs_record_skipped(large_flow):
    runtime = RuntimeFlowgraph(large_flow, prune_nodes=[
        ("stepone", "0"), ("steptwo", "1"), ("stepthree", "2")])

    record = RecordSchema()
    record.set("status", NodeStatus.SKIPPED, step="stepone", index="1")

    assert runtime.get_node_inputs("stepone", "1", record=record) == []
    assert runtime.get_node_inputs("joinone", "0", record=record) == [('stepone', '2')]
    assert runtime.get_node_inputs("steptwo", "0", record=record) == [('joinone', '0')]


def test_get_node_inputs_invalid(large_flow):
    runtime = RuntimeFlowgraph(large_flow, prune_nodes=[
        ("stepone", "0"), ("steptwo", "1"), ("stepthree", "2")])

    with pytest.raises(ValueError, match="^stepone/0 is not a valid node$"):
        runtime.get_node_inputs("stepone", "0")


def test_runtime_get_completed_nodes_no_record(large_flow):
    assert RuntimeFlowgraph(large_flow).get_completed_nodes() == []


def test_runtime_get_completed_nodes_with_record(large_flow):
    record = RecordSchema()
    record.set("status", NodeStatus.SKIPPED, step="stepone", index="1")
    record.set("status", NodeStatus.SUCCESS, step="stepone", index="0")

    assert RuntimeFlowgraph(large_flow).get_completed_nodes(record=record) == [
        ('stepone', '0'), ('stepone', '1')]


def test_runtime_validate_nothing(large_flow):
    assert RuntimeFlowgraph.validate(large_flow) is True


def test_runtime_validate_invalid_steps(large_flow, caplog):
    assert RuntimeFlowgraph.validate(
        large_flow,
        from_steps=["nothere"],
        to_steps=["notthere"], logger=logging.getLogger()) is False

    assert "From nothere is not defined in the testflow flowgraph" in caplog.text
    assert "To notthere is not defined in the testflow flowgraph" in caplog.text


def test_runtime_validate_invalid_node(large_flow, caplog):
    assert RuntimeFlowgraph.validate(
        large_flow,
        prune_nodes=[("notthis", "0")], logger=logging.getLogger()) is False

    assert "notthis/0 is not defined in the testflow flowgraph" in caplog.text


def test_runtime_validate_prune_exits(large_flow, caplog):
    assert RuntimeFlowgraph.validate(
        large_flow,
        prune_nodes=[("jointhree", "0")], logger=logging.getLogger()) is False

    assert "pruning removed all exit nodes for jointhree in the testflow flowgraph" in caplog.text


def test_runtime_validate_prune_entry(large_flow, caplog):
    assert RuntimeFlowgraph.validate(
        large_flow,
        prune_nodes=[("stepone", "0"), ("stepone", "1"), ("stepone", "2")],
        logger=logging.getLogger()) is False

    assert "pruning removed all entry nodes for stepone in the testflow flowgraph" in caplog.text


def test_runtime_validate_prune_entry_valid(large_flow, caplog):
    assert RuntimeFlowgraph.validate(
        large_flow,
        prune_nodes=[("stepone", "0"), ("stepone", "1")], logger=logging.getLogger()) is True


def test_runtime_validate_prune_path(large_flow, caplog):
    assert RuntimeFlowgraph.validate(
        large_flow,
        prune_nodes=[("joinone", "0"), ("stepone", "2")], logger=logging.getLogger()) is False

    assert "no path from stepone/0 to jointhree/0 in the testflow flowgraph" in caplog.text
    assert "no path from stepone/1 to jointhree/0 in the testflow flowgraph" in caplog.text


def test_runtime_validate_disjoint(caplog):
    flow = Flowgraph("testflow")

    flow.node("stepone", "siliconcompiler.tools.builtin.nop/NOPTask")
    flow.node("steptwo", "siliconcompiler.tools.builtin.nop/NOPTask")

    assert RuntimeFlowgraph.validate(
        flow,
        from_steps=["stepone"],
        to_steps=["steptwo"], logger=logging.getLogger()) is False

    assert "no path from stepone/0 to steptwo/0 in the testflow flowgraph" in caplog.text


def test_get_task_module_invalid():
    with pytest.raises(ValueError, match=r"^teststep/testindex is not a valid node in testflow\.$"):
        Flowgraph("testflow").get_task_module("teststep", "testindex")


def test_get_task_module(large_flow):
    assert large_flow.get_task_module("joinone", "0") is JoinTask
    assert large_flow.get_task_module("stepone", "0") is NOPTask


def test_get_task_module_ensure_cache(large_flow):
    assert large_flow.get_task_module("joinone", "0") is JoinTask

    with patch.dict(large_flow._Flowgraph__cache_tasks,
                    {"siliconcompiler.tools.builtin.join/JoinTask": None}):
        assert large_flow.get_task_module("joinone", "0") is None


def test_get_task_module_error(large_flow):
    assert large_flow.set("joinone", "0", "taskmodule", "notvalid.module/cls")
    with pytest.raises(ModuleNotFoundError, match="^No module named 'notvalid'$"):
        large_flow.get_task_module("joinone", "0")


def test_get_task_cls_not_found(large_flow):
    assert large_flow.set("joinone", "0", "taskmodule", "siliconcompiler/notaclass")
    with pytest.raises(AttributeError,
                       match="^module 'siliconcompiler' has no attribute 'notaclass'$"):
        large_flow.get_task_module("joinone", "0")


def test_get_task_formatting_error(large_flow):
    assert large_flow.set("joinone", "0", "taskmodule", "notvalid.module")
    with pytest.raises(ValueError,
                       match=r"^task is not correctly formatted as "
                             r"<module>/<class>: notvalid\.module$"):
        large_flow.get_task_module("joinone", "0")


def test_get_all_tasks(large_flow):
    assert set(large_flow.get_all_tasks()) == set([
        NOPTask, JoinTask
    ])


def test_write_flowgraph(large_flow, has_graphviz):
    large_flow.write_flowgraph("test.png")
    assert os.path.isfile("test.png")


def test_get_task_module_invalid_format():
    with pytest.raises(ValueError,
                       match="^task is not correctly formatted as <module>/<class>: something$"):
        Flowgraph()._Flowgraph__get_task_module("something")


def test_get_task_module_invalid_type():
    with pytest.raises(ValueError,
                       match="^task is not correctly formatted as <module>/<class>: None$"):
        Flowgraph()._Flowgraph__get_task_module(None)
