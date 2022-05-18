Flows
===================================

SiliconCompiler flows are created by configuring the 'flowgraph' parameters within the schema. To simplify reuse of complex flows, the project includes standardized interfaces for bundling flowgraph settings as reusable named modules. These flow modules get loaded by the :meth:`.load_flow()` function during compilation setup. A complete set of supported open PDKs can be found in the :ref:`Flows Directory`. The table below shows the function interfaces required in setting up flows.


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
     - PDK setup function
     - chip
     - chip
     - load_flow()
     - yes

   * - **make_docs**
     - Doc generator
     - None
     - chip
     - sphinx
     - yes


setup(chip)
-----------------

A SiliconCompiler flowgraph consists of a set of connected nodes and edges, where a node is an executable tool performing some ("task"), and an edge is the connection between those tasks. The first task in the flowgraph must be named 'import'. ::

  chip.node(flow, 'import', <import_tool>)
  chip.node(flow, <step>, <step_tool>)
  chip.edge(flow, 'import', <step>)

In addition, the setup needs to define the compilation mode. ::

  chip.set('option', 'mode', 'asic')

Flows that support SiliconCompiler metric functions (minimum, maximum, summary) should also set appropriate metric weights and goals for correct behavior. ::

  for metric in ('errors','drvs','holdwns','setupwns','holdtns','setuptns'):
    chip.set('flowgraph', flow, step, index, 'goal', metric, 0)
  for metric in ('cellarea', 'peakpower', 'standbypower'):
    chip.set('flowgraph', flow, step, index, 'weight', metric, 1.0)

Note that the :keypath:`arg, flow` dictionary in the schema can be used to pass named arguments to configure flow setup. For example, the built-in asicflow and fpgaflow use the 'techarg', 'sv' parameter to enable or disable a SystemVerilog to Verilog conversion step.

For a complete working example, see the `asicflow <https://github.com/siliconcompiler/siliconcompiler/blob/main/siliconcompiler/flows/asicflow.py>`_ and `fpgaflow <https://github.com/siliconcompiler/siliconcompiler/blob/main/siliconcompiler/flows/fpgaflow.py>`_ source code.

make_docs()
-----------------
The make_docs() function is used by the projects auto-doc generation. The function should include a descriptive docstring and a call to the setup function that populates the appropriate schema settings. ::

  def make_docs():
    '''
    A configurable ASIC compilation flow.
    '''

    chip = siliconcompiler.Chip()
    setup(chip)
    return chip
