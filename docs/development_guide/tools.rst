.. _dev_tools:

Tools
=====

SiliconCompiler execution depends on implementing adapter code ("drivers") for each tool which gets called in a flowgraph.
Tools are referenced as named modules by the flowgraph, and searched using the :meth:`.find_files()` method.
A complete set of supported tools can be found in :ref:`tools <builtin_tools>`.

Each tool can support multiple "tasks". Each node in the flowgraph is associated with both a tool and a task.
Shared configurations such as the tool's minimum version number go in the tool modules, and task-specific settings go in the task modules.

For example, the KLayout tool can be used to export GDS files, display results in a GUI window, or take screenshots of a design.
Each of those three functions is associated with a different task name: :ref:`export <tools-klayout-export-ref>`, :ref:`show <tools-klayout-show-ref>`, and :ref:`screenshot <tools-klayout-screenshot-ref>` respectively.

Tool functions
--------------

The table below shows the function interfaces supported in setting up tool logic.

.. list-table::
   :widths: 10 10 10 10 10 10
   :header-rows: 1

   * - Function
     - Description
     - Arg
     - Returns
     - Used by
     - Required

   * - :ref:`setup <tool_setup>`
     - Configures tool
     - :class:`.Chip`
     - n/a
     - :meth:`.run()`
     - yes

   * - :ref:`parse_version <tool_parse_version>`
     - Returns executable version
     - stdout
     - version
     - :meth:`.run()`
     - no

   * - :ref:`normalize_version <tool_normalize_version>`
     - Returns executable version
     - tool version
     - normalized version
     - :meth:`.run()`
     - no

   * - :ref:`make_docs <tool_make_docs>`
     - Doc generator
     - None
     - :class:`.Chip`
     - sphinx
     - no


.. _tool_setup:

setup()
*******

Tool setup is performed for each step and index within the :meth:`.run()` function, prior to launching each individual task.
Tools can be configured independently for different tasks (ie. the place task is different from the route task), so we need a method for passing information about the current step and index to the setup function.
This is accomplished with the reserved parameters shown below.

.. code-block:: python

  step = chip.get('arg','step')
  index = chip.get('arg','index')

Each node in the flowgraph has a step name, and an index.
The step name is linked to a task type by the :meth:`.node()` function, which is usually called in a :class:`Flow`'s :ref:`setup() <flow_setup>` function.
The indices are used to allow multiple instances of a task to run in parallel with slightly different parameters.
When you are not performing a parameter sweep, the "index" value will usually be set to ``"0"``.

All tools are required to bind the tool name to an executable name and to define any required command line options.

.. code-block:: python

  chip.set('tool', <toolname>, 'exe', <exename>)
  chip.set('tool', <toolname>, 'task', <taskname> 'option', <option>)

To leverage the :meth:`.run()` function's internal setup checking logic, it is highly recommend to define the version switch and supported version numbers using the commands below.

.. code-block:: python

  chip.set('tool', <toolname>, 'version' <list[string]>)
  chip.set('tool', <toolname>, 'vswitch', <string>)

.. _tool_parse_version:

parse_version(stdout)
*********************

The :meth:`.run()` function includes built in executable version checking, which can be disabled with the :keypath:`option,novercheck` parameter.
The executable option to use for printing out the version number is specified with the :keypath:`tool, <tool>, vswitch` parameter within the :ref:`setup() <tool_setup>` function.
Commonly used options include '-v', '\-\-version', '-version'.
The executable output varies widely, so we need a parsing function that processes the output and returns a single uniform version string.
The example shows how this function is implemented for the Yosys tool.

.. code-block:: python

  def parse_version(stdout):
      # Yosys 0.9+3672 (git sha1 014c7e26, gcc 7.5.0-3ubuntu1~18.04 -fPIC -Os)
      return stdout.split()[1]  # return 0.9+3672

The :meth:`.run()` function compares the returned parsed version against the :keypath:`tool, <tool>, version` parameter specified in the :ref:`setup() <tool_setup>` function to ensure that a qualified executable version is being used.

.. _tool_normalize_version:

normalize_version(version)
**************************

SC's version checking logic is based on Python's `PEP-440 standard <https://peps.python.org/pep-0440/>`_.
In order to perform version checking for tools that do not natively provide PEP-440 compatible version numbers, this function must be implemented to convert the tool-specific versions to a PEP-440 compatible equivalent.

Note that a raw version number may parse as a valid PEP-440 version but not be semantically correct.
``normalize_version()`` must be implemented in these cases to ensure version comparisons make sense.
For example, we have to do this for Yosys.

.. code-block:: python

  def normalize_version(version):
      # Replace '+', which represents a "local version label", with '-', which is
      # an "implicit post release number".
      return version.replace('+', '-')  # returns 0.9-3672


.. _tool_make_docs:

make_docs(chip)
***************
The ``make_docs()`` function is used by the projects auto-doc generation.
This function is only needed if the tool requires additional inputs to be setup correctly.
The function should include a call to the setup function to populate the schema with all settings as shown below.
The input to this function ``chip`` is a chip object created by the auto-doc generator.

.. code-block:: python

  def make_docs(chip):
    return setup(chip)


Task functions
--------------

The table below shows the function interfaces supported in setting up task logic.

.. list-table::
   :widths: 10 10 10 10 10 10
   :header-rows: 1

   * - Function
     - Description
     - Arg
     - Returns
     - Used by
     - Required

   * - :ref:`setup <task_setup>`
     - Configures task
     - :class:`.Chip`
     - n/a
     - :meth:`.run()`
     - yes

   * - :ref:`runtime_options <task_runtime_options>`
     - Resolves paths at runtime
     - :class:`.Chip`
     - list
     - :meth:`.run()`
     - no

   * - :ref:`pre_process <task_pre_process>`
     - Pre-executable logic
     - :class:`.Chip`
     - n/a
     - :meth:`.run()`
     - no

   * - :ref:`post_process <task_post_process>`
     - Post-executable logic
     - :class:`.Chip`
     - n/a
     - :meth:`.run()`
     - no

   * - :ref:`make_docs <task_make_docs>`
     - Doc generator
     - None
     - :class:`.Chip`
     - sphinx
     - no

   * - :ref:`run <task_run>`
     - Pure Python tool
     - :class:`.Chip`
     - exit code
     - :meth:`.run()`
     - no


.. _task_setup:

setup()
*******

Task setup is performed for each step and index within the :meth:`.run()` function, prior to launching each individual task.
Just as it is done for a tool.

For tools such as TCL based EDA tools, we also need to define the entry script and any associated script directories.

.. code-block:: python

  chip.set('tool', <toolname>, 'task', <taskname>, 'script', <entry_script>)
  chip.set('tool', <toolname>, 'task', <taskname>, 'refdir', <scriptdir>)
  chip.set('tool', <toolname>, 'task', <taskname>, 'format', <scriptformat>)

To leverage the :meth:`.run()` function's internal setup checking logic, it is highly recommend to define the parameter requirements, required inputs, expected output using the commands below.

.. code-block:: python

  chip.set('tool', <toolname>, 'task', <taskname>, 'input', <list[file]>)
  chip.set('tool', <toolname>, 'task', <taskname>, 'output', <list[file]>)
  chip.set('tool', <toolname>, 'task', <taskname>, 'require' <list[string]>)
  chip.set('tool', <toolname>, 'task', <taskname>, 'report', <list[file]>)


.. _task_pre_process:

pre_process(chip)
*****************

For certain tools and tasks, we may need to set some Schema parameters immediately before task execution.
For example, we may want to set the die and core area before the floorplan step based on the area result from the synthesis step or to handle preprocessing of a file to make it compatible with the tool.

.. _task_post_process:

post_process(chip)
******************

The post process step is required to extract metrics from the tool log files, if the task does not collect anything then this function can be omitted.

The post_process function can also be used to post process the output data in the case of command line executable to produce an output that can be ingested by the SiliconCompiler framework.
The Surelog ``post_process()`` implementation illustrates the power of the this functionality.

.. code-block:: python

  def post_process(chip):
    ''' Tool specific function to run after step execution
    '''
    design = chip.top()
    step = chip.get('arg', 'step')

    # Look in slpp_all/file_elab.lst for list of Verilog files included in
    # design, read these and concatenate them into one pickled output file.
    with open('slpp_all/file_elab.lst', 'r') as filelist, \
            open(f'outputs/{design}.v', 'w') as outfile:
        for path in filelist.read().split('\n'):
            if not path:
                # skip empty lines
                continue
            with open(path, 'r') as infile:
                outfile.write(infile.read())
            # in case end of file is missing a newline
            outfile.write('\n')

.. _task_runtime_options:

runtime_options(chip)
*********************

The distributed execution model of SiliconCompiler mandates that absolute paths be resolved at task run time.
The :ref:`setup <task_setup>` function is run at :meth:`.run()` launch to check flow validity, so we need a second function interface (``runtime_options()``) to create the final commandline options.
The ``runtime_options()`` function inspects the Schema and returns a cmdlist to be used by the 'exe' during task execution.
The sequence of items used to generate the final command line invocation is as follows: ::

  <'tool',...,'exe'> <'tool',...,'option'> <'tool',...,'script'> <runtime_options()>

The example below illustrates the process of defining a ``runtime_options()`` function.

.. code-block:: python

  def runtime_options(chip):
    '''
    Custom runtime options, returns list of command line options.
    '''

    step = chip.get('arg','step')
    index = chip.get('arg','index')

    cmdlist = []

    # source files
    for value in chip.find_files('option', 'ydir'):
        cmdlist.append('-y ' + value)
    for value in chip.find_files('option', 'vlib'):
        cmdlist.append('-v ' + value)
    for value in chip.find_files('option', 'idir'):
        cmdlist.append('-I' + value)
    for value in chip.get('option', 'define'):
        cmdlist.append('-D' + value)
    for value in chip.find_files('option', 'cmdfile'):
        cmdlist.append('-f ' + value)
    for value in chip.find_files('option', 'source'):
        cmdlist.append(value)

    cmdlist.append('-top ' + chip.top())
    # make sure we can find .sv files in ydirs
    cmdlist.append('+libext+.sv')

    # Set up user-provided parameters to ensure we elaborate the correct modules
    for param in chip.getkeys('option', 'param'):
        value = chip.get('option', 'param', param)
        cmdlist.append(f'-P{param}={value}')

    return cmdlist

.. _task_make_docs:

make_docs(chip)
***************

The ``make_docs()`` function is used by the projects auto-doc generation.
This function is only needed if the task requires additional inputs to be setup correctly.
The function should include a call to the setup function to populate the schema with all settings as shown below.
The input to this function ``chip`` is a chip object created by the auto-doc generator.

.. code-block:: python

  def make_docs(chip):
    return setup(chip)


.. _task_run:

run(chip)
*********

SiliconCompiler supports pure-Python tools that execute a Python function rather than an executable.
To define a pure-Python tool, add a function called ``run()`` in your tool driver, which takes in a Chip object and implements your tool's desired functionality.
This function should return an integer exit code, with zero indicating success.

Note that pure-Python tool drivers still require a ``setup()`` function, but most :keypath:`tool` fields will not be meaningful.
At the moment, pure-Python tools do not support the following features:

* Version checking
* Replay scripts
* Task timeout
* Memory usage tracking
* Breakpoints
* Output redirection/regex-based logfile parsing


TCL interface
--------------

.. note::

   SiliconCompiler configuration settings are communicated to all script based tools as TCL nested dictionaries.

Schema configuration handoff from SiliconCompiler to script based tools is accomplished within the :meth:`.run()` function by using the :meth:`.write_manifest()` function to write out the complete schema as a nested TCL dictionary.
A snippet of the resulting TCL dictionary is shown below.

.. code-block:: tcl

   dict set sc_cfg asic logiclib [list "NangateOpenCellLibrary" ]
   dict set sc_cfg asic macrolib [list ]
   dict set sc_cfg design [list "gcd" ]
   dict set sc_cfg option frontend [list "verilog"]

This generated manifest also includes a helper function, ``sc_top``, that handles the logic for determining the name of the design's top-level module (mirroring the logic of :meth:`.top()`).

It is the responsibility of the tool reference flow developer to bind the standardized SiliconCompiler TCL schema to the tool specific TCL commands and variables.
The TCL snippet below shows how the `OpenRoad TCL reference flow <https://github.com/siliconcompiler/siliconcompiler/blob/main/siliconcompiler/tools/openroad/scripts/sc_apr.tcl>`_ remaps the TCL nested dictionary to simple lists and scalars at the beginning of the flow for the sake of clarity.

.. code-block:: tcl

   #Design
   set sc_design     [sc_top]
   set sc_tool       <toolname>
   set sc_optmode    [sc_cfg_get optmode]

   # APR Parameters
   set sc_mainlib     [lindex [sc_cfg_get asic logiclib] 0]
   set sc_stackup     [sc_cfg_get option stackup]
   set sc_targetlibs  [sc_cfg_get asic logiclib]
   set sc_density     [sc_cfg_get constraint density]
   set sc_pdk         [sc_cfg_get option pdk]
   set sc_hpinmetal   [lindex [sc_cfg_get pdk $sc_pdk {var} $sc_tool pin_layer_horizontal $sc_stackup] 0]
   set sc_vpinmetal   [lindex [sc_cfg_get pdk $sc_pdk {var} $sc_tool pin_layer_vertical $sc_stackup] 0]
