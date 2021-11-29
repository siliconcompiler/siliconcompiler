Tools
===================================

Tools are referenced as named modules by the execution flowgraph. At runtime, the run() searches for a tool module at 'siliconcompiler/tools/<toolname>/<toolname>.py'. The module search path can be expanded by adding paths to the 'scpath' parameter or the $SCPATH environment variable. Tool setup modules must include one or more of the functions from the list below.

.. list-table::
   :widths: 10 10 10 10 10 10
   :header-rows: 1

   * - Function
     - Description
     - Arg
     - Returns
     - Used by
     - Required

   * - **setup_tool**
     - Configures tool
     - chip
     - chip
     - run()
     - yes

   * - **runtime_options**
     - Resolves paths at runtime
     - chip
     - list
     - run()
     - no

   * - **parse_version**
     - Returns executable version
     - stdout
     - version
     - run()
     - yes

   * - **pre_process**
     - Pre-executable logic
     - chip
     - chip
     - run()
     - no

   * - **post_process**
     - Post-executable logic
     - chip
     - chip
     - run()
     - no

   * - **make_docs**
     - Doc generator
     - chip
     - chip
     - sphinx
     - no

For a complete example of a tool setup module, see `OpenROAD <https://github.com/siliconcompiler/siliconcompiler/blob/main/siliconcompiler/tools/openroad/openroad.py>`_. For more in depth information about the various 'eda' parameters, see the :ref:`Schema` section of the reference manual.


setup_tool(chip)
-----------------

Tool setup is done for each step and index at runtime so two schema 'scratch' parameters are used to pass in the information needed for recording the setup information cirrectly in the schema.::

  step = chip.get('arg','step')
  index = chip.get('arg','index')

All tools are required to bind the toolname to an executable name and to define any required command line options.::

  chip.set('eda', <toolname>, step, index, 'exe', <exename>)
  chip.set('eda', <toolname>, step, index, 'option', 'cmdline', <option>)

For tools such as TCL based EDA tools, we also need to define the entry script and any associated script directories.::

  chip.set('eda', <toolname>, step, index, 'script', <entry_script>)
  chip.set('eda', <toolname>, step, index, 'refdir', <scriptdir>)
  chip.set('eda', <toolname>, step, index, 'format', <scripformat>)

In addition, to leverage the run() function error checking logic, it is highly recommend to define the parameter requirements, required inputs, expected output, version switch, and supported version numbers using the commands below::

  chip.set('eda', <toolname>, step, index, 'input', <list>)
  chip.set('eda', <toolname>, step, index, 'output', <list>)
  chip.set('eda', <toolname>, step, index, 'require', <list>)
  chip.set('eda', <toolname>, step, index, 'version', <list>)
  chip.set('eda', <toolname>, step, index, 'vswitch', "<string>")
  chip.set('eda', <toolname>, step, index, 'report', "<list>")

runtime_options(chip)
-----------------------

parse_version(stdout)
-----------------------

pre_process(chip)
-----------------------

post_process(chip)
-----------------------

make_docs()
-----------------------


TCL interface
--------------

.. note::

   The manifest/schema is the only supported method for communicating between SiliconCompiler and tools.

Schema configuration handoff from SiliconCompiler to script based tools is accomplished in within the run() function by using the write_manifest() function to write out the complete schema as a nested TCL dictionary. A snippet of the resulting TCL dictionary is shown below.

.. code-block:: tcl

   dict set sc_cfg asic targetlib [list  NangateOpenCellLibrary ]
   dict set sc_cfg asic maxfanout [list  64 ]
   dict set sc_cfg design [list  gcd ]
   dict set sc_cfg constraint [list gcd.sdc ]
   dict set sc_cfg source [list gcd.v ]

It is the responsibility of the tool reference flow developer to bind the standardized SiliconCompiler TCL schema to the tool specific TCL commands and variables.
