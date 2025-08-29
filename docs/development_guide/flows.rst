.. _dev_flows:

Flows
=====

SiliconCompiler flows are created by configuring a :class:`.FlowgraphSchema` or creating a new child class of :class:`.FlowgraphSchema`.

Flows are loaded by passing a :class:`.FlowgraphSchema` object into the :meth:`.Project.add_dep()` or :meth:`.Project.set_flow()` function before a run is started.
:class:`.FlowgraphSchema` objects typically use the :meth:`.FlowgraphSchema.node()` and :meth:`.FlowgraphSchema.edge()` functions to configure a "flowgraph" which represents a hierarchical collection of tasks to execute.

A complete set of supported open flows can be found in :ref:`flows <builtin_flows>`.

Example
-------

Then following example demonstrates a basic asic synthesis flow.

.. code-block:: python

  from siliconcompiler import FlowgraphSchema
  from siliconcompiler.tools.yosys import syn_asic
  from siliconcompiler.tools.opensta import timing
  from siliconcompiler.tools.slang import elaborate


  class SynthesisFlow(FlowgraphSchema):
      def __init__(self):
          super().__init__("testflow")

          self.node("elaborate", elaborate.Elaborate())

          self.node("synthesis", syn_asic.ASICSynthesis())
          self.edge("elaborate", "synthesis")

          self.node("timing", timing.TimingTask())
          self.edge("synthesis", "timing")


Useful APIs
-----------

Create flowgraphs
^^^^^^^^^^^^^^^^^

.. currentmodule:: siliconcompiler.FlowgraphSchema

.. autosummary::
    :nosignatures:

    node
    edge

Edit flowgraghs
^^^^^^^^^^^^^^^

.. autosummary::
    :nosignatures:

    remove_node
    insert_node
    graph

Access flowgraghs
^^^^^^^^^^^^^^^^^

.. autosummary::
    :nosignatures:

    get_nodes
    get_entry_nodes
    get_exit_nodes
    get_execution_order
    get_node_outputs
    validate
    get_task_module
    get_all_tasks
    write_flowgraph

Documentation
^^^^^^^^^^^^^

.. autosummary::
    :nosignatures:

    make_docs

Class API
---------

.. autoclass:: siliconcompiler.FlowgraphSchema
    :members:
    :show-inheritance:
    :inherited-members:

Support classes
---------------

.. autoclass:: siliconcompiler.flowgraph.FlowgraphNodeSchema
    :members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: siliconcompiler.flowgraph.RuntimeFlowgraph
    :members:
    :show-inheritance:
    :inherited-members:
