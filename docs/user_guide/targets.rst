Targets
===================================

To facilitate encapsulation and reuse of schema parameters related to design targets, SiliconCompiler implements a :meth:`.load_target()` function that dynamically loads Python modules located in special places on the filesystem.

:meth:`.load_target()` takes in a string ``targetname``, and it will search for the path ``targets/<targetname>.py`` in the following locations, in this order:

  #. The working directory from where the CLI app was called or the :class:`.Chip()` object instantiated.
  #. Paths specified in the :keypath:`option, scpath` schema parameter, separated by the OS-specific path separator (``:`` on Linux/macOS, ``;`` on Windows).
  #. Paths specified in the $SCPATH environment variable, separated by the OS-specific path separator.
  #. The root of the SiliconCompiler Python package, wherever it is installed.

The ability to configure the search paths via a schema parameter or environment variable enables users to create custom targets and place them anywhere on their filesystem. Note that this file resolution scheme is also used by SC for resolving all other relative paths, not just target modules.

All target modules must contain a function ``setup()`` that takes in a chip object and can modify its schema parameters in any way. It's common for targets to load at least one flow, a PDK and at least one standard cell library if an ASIC target, and sometimes set up default design parameters. Targets should also include a ``make_docs()`` function which provides a descriptive docstring and returns a chip object with the target loaded.

SC supports additional levels of encapsulation through PDK, library, and flow modules. These are loaded similarly to targets, but with their own respective load functions and directories, as shown below:

.. list-table::
   :widths: 40 40
   :header-rows: 1

   * - Function
     - Module location

   * - :meth:`load_pdk(name) <.load_pdk>`
     - ``pdks/<name>.py``

   * - ``load_lib(name)``
     - ``libs/<name>.py``

   * - ``load_flow(name)``
     - ``flows/<name>.py``

See the :ref:`PDK<PDKs>`, :ref:`Library<Libraries>`, and :ref:`Flow<Flows>` User Guide pages to learn more about what is expected to be configured in each of these modules.

Generally, these functions will be called by targets, and then a user will only have to call :meth:`.load_target()` in their build script.  However, the :meth:`run()` function requires all mandatory flowgraph, pdk, and tool settings to be defined prior to execution, so if a partial target is loaded, additional setup may be required.

The following example calls the :meth:`.load_target()` function to load the built-in :ref:`freepdk45_demo` target. ::

  chip.load_target('freepdk45_demo')

The following example demonstrates the functional equivalent at the command line:

.. code-block:: bash

   sc -input "verilog hello.v" -target "freepdk45_demo"

A full list of built-in demo targets can be found on the :ref:`Targets directory` page.
