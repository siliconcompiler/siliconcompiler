Targets
===================================

To faciliate grouping and encapsulation of schema parameters, SiliconCompiler implements a target() function that operates on string based names similar to `LLVM <https://clang.llvm.org/docs/CrossCompilation.html>`_. The target() function searches for Python modules that match strings extracted from a "_" delimetered target string. Depending on the target type, target() will construct a relative path as follows:

  * **Tools**: ``tools/<modulename>/<modulename>.py``
  * **Flows**: ``flows/<modulename>.py``
  * **PDKs**: ``pdks/<modulname>.py``

target() will then search for these relative paths in the following locations, in this order:

  #. The root of the SiliconCompiler Python package, wherever it is installed.
  #. The working directory from where the CLI app was called or the Chip() object instantiated.
  #. Paths specified in the 'scpath' schema parameter, separated by the OS-specific path separator (``:`` on Linux/macOS, ``;`` on Windows).
  #. Paths specified in the $SCPATH environment variable, separated by the OS-specific path separator.

The ability to configure the search paths via a schema parameter or environment variable enables users to create custom targets and place them anywhere on their filesystem. Note that this file resolution scheme is also used by SC for resolving all other relative paths, not just target modules.

The run() function requires all mandatory flowgraph, pdk, and tool settings to be defined prior to exection, so if a partial target is loaded, additional parameter set() calls may be required. The following example calls the target function to load the setup_flow() function for asicflow and setup_pdk function for freepdk45. ::

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
