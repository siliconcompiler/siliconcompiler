Flows
=====

SiliconCompiler flows are created by configuring the :keypath:`flowgraph` parameters within the schema.
To simplify reuse of complex flows, the project includes standardized interfaces for bundling flowgraph settings as reusable named modules.

Similar to other types of SiliconCompiler modules, flows are loaded by passing a :class:`siliconcompiler.Flow` object into the :meth:`.use()` function before a run is started. :class:`siliconcompiler.Flow` objects typically use the :meth:`.node()` and :meth:`.edge()` functions to configure a "flowgraph" which represents a hierarchical collection of tasks to execute.

setup()
-----------------

A SiliconCompiler flowgraph consists of a set of connected nodes and edges, where a node is an executable tool performing some ("task"), and an edge is the connection between those tasks.
The first task in the flowgraph must be named 'import'. ::

  flow.node(flow, 'import', <import_tool>, 'import')
  flow.node(flow, <next_step>, <next_tool>, <next_task>)
  flow.edge(flow, 'import', <next_step>)

Flows that support SiliconCompiler metric functions (minimum, maximum, summary) should also set appropriate metric weights and goals for correct behavior. ::

  for metric in ('errors','drvs','holdwns','setupwns','holdtns','setuptns'):
    flow.set('flowgraph', flow, step, index, 'goal', metric, 0)
  for metric in ('cellarea', 'peakpower', 'standbypower'):
    flow.set('flowgraph', flow, step, index, 'weight', metric, 1.0)

For a complete working example, see the `asicflow <https://github.com/siliconcompiler/siliconcompiler/blob/main/siliconcompiler/flows/asicflow.py>`_ and `fpgaflow <https://github.com/siliconcompiler/siliconcompiler/blob/main/siliconcompiler/flows/fpgaflow.py>`_ source code.

make_docs()
-----------------

The ``make_docs()`` function is used by the projects auto-doc generation.
The function should include a descriptive docstring and a call to the setup function that populates the appropriate schema settings. ::

  def make_docs(chip):
    '''
    A configurable ASIC compilation flow.
    '''

    setup()
    return chip

Flow Modules
------------

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

   * - **setup**
     - Flow setup function
     - :class:`.Chip`
     - :class:`siliconcompiler.Flow`
     - :meth:`.use()`
     - yes

   * - **make_docs**
     - Doc generator
     - :class:`.Chip`
     - :class:`siliconcompiler.Flow`
     - sphinx
     - no

A complete set of supported open flows can be found in :ref:`flows`.
