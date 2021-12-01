Targets
===================================

To faciliate grouping and encapsulation of schema parameters, SiliconCompiler implements a target() function that operates on string based names similar to `LLVM <https://clang.llvm.org/docs/CrossCompilation.html>`_. The target() function searches the 'scpath' parameter for Python modules that match strings extracted from a "_" delimetered target string. The run() function requires all mandatory flowgraph, pdk, and tool settings to be defined prior to exection, so if a partial target is loaded, additional parameter set() calls may be required. The following example calls the target function to load the setup_flow() function for asicflow and setup_pdk function for freepdk45. ::

  chip.target('asicflow_freepdk45')

The following example demonstrates the functional equivalent at the command line:

.. code-block:: bash

   sc hello.v -target "asicflow_freepdk45"

The following target target string combinations are supported:

 * <flowname>
 * <flowname>_<pdkname>
 * <flowname>_<partname> (for fpga flows)
 * <pdk>
 * <tool>
 * <tool>_<pdkname>
 * <projname>

Loading tools through the target requires setting a step argument since tools are set up on a per step and per index basis. The example below illustrates the use of target to load tools individually. ::

  chip.set('arg','step', 'floorplan')
  chip.target("openroad_freepdk45")
  chip.run()
