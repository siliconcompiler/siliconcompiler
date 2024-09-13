.. _dev_flows:

Flows
=====

SiliconCompiler flows are created by configuring the :keypath:`flowgraph` parameters within the schema.
To simplify reuse of complex flows, the project includes standardized interfaces for bundling flowgraph settings as reusable named modules.

Similar to other types of SiliconCompiler modules, flows are loaded by passing a :class:`.Flow` object into the :meth:`.use()` function before a run is started. :class:`.Flow` objects typically use the :meth:`.node()` and :meth:`.edge()` functions to configure a "flowgraph" which represents a hierarchical collection of tasks to execute.
A complete set of supported open flows can be found in :ref:`flows <builtin_flows>`.


Functions
---------

The table below shows the function interfaces for setting up Flow objects.

.. list-table::
   :widths: 10 10 10 10 10 10
   :header-rows: 1

   * - Function
     - Description
     - Arg
     - Returns
     - Used by
     - Required

   * - :ref:`setup() <flow_setup>`
     - Flow setup function
     - optional keyword arguments
     - :class:`.Flow`
     - :meth:`.use()`
     - yes

   * - :ref:`make_docs() <flow_make_docs>`
     - Doc generator
     - :class:`.Chip`
     - :class:`.Flow`
     - sphinx
     - no

.. _flow_setup:

setup()
-------

A SiliconCompiler flowgraph consists of a set of connected nodes and edges, where a node is an executable tool performing some ("task"), and an edge is the connection between those tasks.
To configure the flow, the following helper methods are available :meth:`.node()` to create a new node in the graph and :meth:`.edge()` to create an edge between nodes.

.. code-block:: python

  from siliconcompiler import Flow
  from siliconcompiler.tools.surelog import parse
  from siliconcompiler.tools.yosys import syn_asic

  flowname = '<flowname>'
  flow = Flow(flowname)
  flow.node(flowname, <node name0>, parse)
  flow.node(flowname, <node name1>, syn_asic)
  flow.edge(flowname, <node name0>, <node name1>)

Flows that support SiliconCompiler metric functions (:ref:`minimum <tools-builtin-minimum-ref>`, :ref:`maximum <tools-builtin-maximum-ref>`, :ref:`verify <tools-builtin-verify-ref>`, and :ref:`mux <tools-builtin-mux-ref>`) should also set appropriate metric weights and goals for correct behavior.

.. code-block:: python

  for metric in ('errors','drvs','holdwns','setupwns','holdtns','setuptns'):
    flow.set('flowgraph', flowname, step, index, 'goal', metric, 0)
  for metric in ('cellarea', 'peakpower', 'standbypower'):
    flow.set('flowgraph', flowname, step, index, 'weight', metric, 1.0)

For a complete working example, see the `asicflow <https://github.com/siliconcompiler/siliconcompiler/blob/main/siliconcompiler/flows/asicflow.py>`_ and `fpgaflow <https://github.com/siliconcompiler/siliconcompiler/blob/main/siliconcompiler/flows/fpgaflow.py>`_ source code.


.. _flow_make_docs:

make_docs(chip)
---------------

The ``make_docs()`` function is used by the projects auto-doc generation.
This function is only needed if the flow requires additional inputs to be setup correctly.
The function should include a call to the setup function to populate the schema with all settings as shown below.
The input to this function ``chip`` is a chip object created by the auto-doc generator.

.. code-block:: python

  def make_docs(chip):
    return setup()
