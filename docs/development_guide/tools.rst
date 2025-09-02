.. _dev_tools:

A complete set of supported tools can be found in :ref:`tools <builtin_tools>`.

Integrating a New Tool
======================

To add support for a new EDA tool, you need to create a Python-based "driver" that teaches SiliconCompiler how to interact with it. Think of a driver as a universal adapter: it translates SiliconCompiler's standardized hardware compilation flow into the specific commands, scripts, and file formats that a particular tool understands.

A complete driver consists of:

* **One or more Task classes**: Defines a specific job that the tool can perform, such as synthesis (syn) or place-and-route (place). Each task specifies its inputs, outputs, and how to generate the command-line arguments.

A complete list of built-in tools can be found in the :ref:`Tools <builtin_tools>` reference.

The Structure of a Tool Driver
------------------------------

A tool driver is a Python module that typically defines at least one :class:`.TaskSchema` class.

.. code-block:: python

  from siliconcompiler import TaskSchema

  class MyTask(TaskSchema):
      """A task for running the tool in a specific way."""
      # Task-level implementation goes here.

      def setup(self):
          # This is the main configuration method.
          pass

      # Other required methods (runtime_options, post_process, etc.)

The setup() Method: Core Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :meth:`.TaskSchema.setup()` method is the heart of the driver. It's called for each step in the flow and is responsible for configuring all aspects of the tool and task.
Inside this method, you have access to the project object to define your settings.

Step 1: Basic Tool Configuration
""""""""""""""""""""""""""""""""

First, you tell SiliconCompiler about the tool's executable and how to check its version.

.. code-block:: python

  def setup(self):
      # Get the tool and task name for the current step.
      tool = self.tool
      task = self.task

      # 1. Point to the executable.
      self.set_exe('my_tool_binary')

      # 2. Define how to check the version.
      #    'vswitch' is the command-line flag to print the version.
      #    'version' is a list of known-good version specifiers.
      self.add_vswitch('--version')
      self.add_version('>=2.1')

Step 2: Task-Specific Configuration
"""""""""""""""""""""""""""""""""""

Next, you define what the specific task needs to run and what it will produce.

.. code-block:: python

  def setup(self):
      # ... (tool setup from above)

      # 3. Define required inputs.
      #    This tells SC to expect a Verilog file from the 'input' node.
      self.add_input_file('verilog.v')

      # 4. Define expected outputs.
      #    This tells SC that this task will produce a new Verilog netlist.
      self.add_output_file('verilog.vg')

      # 5. Define required schema parameters.
      #    This ensures the flow will fail early if a critical setting is missing.
      self.add_required_key('asic', 'pdk')
      self.add_required_key('asic', 'logiclib')

      # 6. For script-based tools (like TCL), define the entry script.
      self.set_script('run_my_tool.tcl')

Execution Lifecycle Methods
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Beyond the initial setup, a :class:`.TaskSchema` class implements several methods that are called at different points during the :meth:`.TaskSchema.run()` process.

runtime_options()
"""""""""""""""""

This method generates the command-line options for the tool. It is called at execution time, which is critical for distributed systems where absolute file paths are only known on the execution machine.

**Why is this separate from setup()?** :meth:`.TaskSchema.setup()` is run early to validate the entire flow, while :meth:`.TaskSchema.runtime_options()` runs just-in-time to build the command, ensuring all paths are resolved correctly.

.. code-block:: python

  def runtime_options(self):
      '''
      Generates the command-line arguments for the tool.
      '''
      cmdlist = []

      # Get a list of all Verilog source files.
      cmdlist.append("verilog.v")

      # Add the output file path.
      cmdlist.append('-o verilog.vg')

      # Add the top module name.
      cmdlist.append(f'-top {self.design_topmodule}')

      return cmdlist

post_process()
""""""""""""""

This method is called after the tool executable has finished. Its primary purpose is to parse log files and report metrics back to the SiliconCompiler database. It can also be used to modify or reformat output files.

.. code-block:: python

  def post_process(self):
      '''
      Parses tool output and reports metrics.
      '''
      # Get the path to the log file for this step.
      log_file = self.get_logpath("exe")

      # Example: Parse the log file for the final cell area.
      with open(log_file, 'r') as f:
          for line in f:
              if line.startswith('Final Area:'):
                  area = float(line.split()[-1])
                  # Record the metric in the SC database.
                  self.record_metric('cellarea', area, 'um^2')

pre_process() and run()
"""""""""""""""""""""""

* :meth:`.TaskSchema.pre_process()`: A hook that runs immediately before the tool executable is launched. Useful for last-minute adjustments based on results from prior steps.
* :meth:`.TaskSchema.pre_process()`: For pure-Python tools. If this method is defined, SiliconCompiler will execute this Python function instead of an external command-line executable. It should return 0 on success.

Version Handling
^^^^^^^^^^^^^^^^

To ensure reproducible builds, SiliconCompiler has a robust version-checking system. You may need to implement these helper methods in your Tool class.

* :meth:`.TaskSchema.parse_version()`: The output of exe --version can be messy. This function parses the raw stdout string and returns a clean version number (e.g., "2.1.3").
* :meth:`.TaskSchema.normalize_version()`: SC's version checker uses the Python PEP-440 standard. If your tool uses a non-standard versioning scheme (e.g., 2.1+a4b8c1), this function should convert it to a compatible format (e.g., 2.1.post0.dev-a4b8c1).

Interface for TCL-Based Tools
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For tools that are driven by TCL scripts, SiliconCompiler simplifies configuration by writing a manifest file (`sc_manifest.tcl`) in the work directory.
Your TCL script should source this file. It provides a nested TCL dictionary called sc_cfg containing the entire project configuration.

Your TCL script is responsible for reading from this dictionary and applying the settings.

.. code-block:: tcl

  # In your run_my_tool.tcl script:

  # Source the manifest to load the configuration
  source sc_manifest.tcl

  # Helper function to get the top-level module name
  set sc_design [sc_top]

  # Extract values from the configuration dictionary
  set sc_asiclibs [sc_cfg_get asic asiclib]
  set sc_pdk      [sc_cfg_get asic pdk]

  # Now use these TCL variables to run tool-specific commands
  read_liberty -lib $sc_asiclibs
  ...

API Quick Reference
-------------------

The :class:`.TaskSchema` class provides a rich API for defining and controlling how a tool operates. The methods are grouped below by their primary function.

.. currentmodule:: siliconcompiler.TaskSchema

Task __init__ methods
^^^^^^^^^^^^^^^^^^^^^

.. autosummary::
    :nosignatures:

    add_parameter

Core Implementation Methods
^^^^^^^^^^^^^^^^^^^^^^^^^^^

These are the main methods you will implement in your :class:`.TaskSchema` subclass to define its behavior.

.. autosummary::
    :nosignatures:

    tool
    task
    parse_version
    normalize_version
    setup
    pre_process
    runtime_options
    run
    post_process

Configuration Methods
^^^^^^^^^^^^^^^^^^^^^

These methods are called within your :meth:`.TaskSchema.setup()` implementation to configure the task's properties.

Tools settings
""""""""""""""

.. autosummary::
    :nosignatures:

    set_exe
    set_path
    add_version
    add_vswitch
    add_licenseserver
    add_sbom

Task settings
"""""""""""""

.. autosummary::
    :nosignatures:

    add_commandline_option
    add_input_file
    add_output_file
    add_parameter
    add_postscript
    add_prescript
    add_regex
    add_required_key
    add_required_tool_key
    add_warningoff
    set_environmentalvariable
    set_logdestination
    set_refdir
    set_script
    set_threads

Runtime Accessor Methods
^^^^^^^^^^^^^^^^^^^^^^^^

These methods are used to get information about the current state of the flow during execution (e.g., inside :meth:`.TaskSchema.runtime_options()` or :meth:`.TaskSchema.post_process()`).

.. autosummary::
    :nosignatures:

    compute_input_file_node_name
    design_name
    design_topmodule
    get_commandline_options
    get_files_from_input_nodes
    get_fileset_file_keys
    get_logpath
    get_output_files
    get_threads
    has_breakpoint
    has_postscript
    has_prescript
    index
    nodeworkdir
    record_metric
    schema
    step
    task
    tool

Tool post process methods
^^^^^^^^^^^^^^^^^^^^^^^^^

.. autosummary::
    :nosignatures:

    record_metric

Documentation methods
^^^^^^^^^^^^^^^^^^^^^

These methods are used for auto-generating documentation for your tool.

.. autosummary::
    :nosignatures:

    make_docs

Class Reference
---------------

.. autoclass:: siliconcompiler.TaskSchema
    :members:
    :show-inheritance:
    :inherited-members:
