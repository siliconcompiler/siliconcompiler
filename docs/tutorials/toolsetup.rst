Tool setup
=======================

Setup requirements
------------------

Executable tools are setup for SC from Python modules (files) named <toolname>_setup.py and placing the file at siliconcompiler/tools/<toolname>.

The tool python module must include a single function show below that gets called
at runtime to dynamically configure the tool. The tool setup is inserted into the SC object being compiled using the 'chip' reference input, step dictionary key, and index dictionary key. The step and index keys allows unique tool configuration on a per step and per index basis::

  def setup_tool(chip, step, index, mode='batch'):
  '''

  '''

As an option, the tool setup can also include a pre process and post process function hooks that get called at run time to handle special processing needed before and after the tool is run. If implemented, the post-process function should return a 0 on successul exit. ::

  def pre_process(chip, step, index):

  def post_process(chip, step, index):


Command line tools
----------------------------
Setting up a command line tool for SC requires a minimum of two parameters:
 * A parameter that defines that name of the executable to be called
 * A parameter that defines how data is passed to the tool at the command line

As a trivial example consider the hypothetical example of setting up 'gcc' for SC.
Let's call the tool "gcc".

.. code-block:: console

  $ gcc hello_world.c

The executable would first need to be connected to that reference name used by SC to define a compilation. The executable name could be something like gcc, g++, gcc-0, gcc-8,or something different depending on the system we are using. Further, GCC requires an input file to be entered for compilation, so we will need to define how we pass in that information to gcc. SC also takes a minimum of one input source file as an argument so this makes for a straightforward mapping.

The code below shows the basic Python code needed to configure the SC schema for GCC::

 tool = 'gcc'
 chip.set('eda', tool, step, index, 'exe', 'gcc-8')
 for item in chip.get('source'):
     chip.add('eda', tool, step, index, 'option', 'cmdline', item)

Note that the code above is designed to be embedded within a run command that runs on a per step and per thread/index basis, so these are kept as variables in the example below. Some key aspects to consider from the example above:
 * The 'exe' key is used to define the name of of the executable, in this case 'gcc-8'
 * The ['option', 'cmdline'] key combo is used to create a list options for the executable.

The GCC tool has many more options that could be driven. Some of those options have correlating
options in SC (-D, -I, ..) for ease of use while special cases would be driven in through the general
['option', 'cmdline'] key combo


Tools with scripting interfaces
--------------------------------

Many EDA style tools are too complicated to be driven purely through a set of static ommand line switches. Instead, the generally take a program (TCl or Python) as an input. As an example, let's step through the the 'openroad' tool setup, which can be found here [TODO: add link]. The handoff from the SC schema to the TCL script is accomplished by saving the entire SC schema as a nested TCL dictionary and reading in the dictionary at the beginnning of the TCL script.

An excerpt of the OpenRoad basic setup is show below, for the complete setup, see the source code here.[TODO add link]::

  def setup_tool(chip, step, index, mode='batch'):
     tool = 'openroad'
     refdir = 'siliconcompiler/tools/openroad'
     script = '/sc_apr.tcl'
     option = "-no_init -exit"
     clobber = False
     chip.set('eda', tool, step, index, 'exe', tool, clobber=clobber)
     chip.set('eda', tool, step, index, 'vswitch', '-version', clobber=clobber)
     chip.set('eda', tool, step, index, 'version', '0', clobber=clobber)
     chip.set('eda', tool, step, index, 'threads', os.cpu_count(), clobber=clobber)
     chip.set('eda', tool, step, index, 'option', 'cmdline', option, clobber=clobber)
     chip.set('eda', tool, step, index, 'refdir', refdir, clobber=clobber)
     chip.set('eda', tool, step, index, 'script', refdir + script, clobber=clobber)
     chip.set('eda', tool, step, index, 'option', 'cmdline', option, clobber=clobber)

First we set up the executable. In this case the name of the tool and executable is the same, 'openroad'::

 chip.set('eda', tool, step, index, 'exe', tool, clobber=clobber)

Next, we specify the name of the version switch and required default version to ket us check the executable version numbers at runtime::

 chip.set('eda', tool, step, index, 'vswitch', '-version', clobber=clobber)
 chip.set('eda', tool, step, index, 'version', '0', clobber=clobber)

We define per index paralleism through the thread parameter. This value can be overriden by the user at configuration time if needed::

  chip.set('eda', tool, step, index, 'threads', os.cpu_count(), clobber=clobber)

We then define where to take the main TCL entry script from and any associated reference flow directories. The ref directory is levereaged within the TCL code to create relative paths::

   chip.set('eda', tool, step, index, 'refdir', refdir, clobber=clobber)
   chip.set('eda', tool, step, index, 'script', refdir + script, clobber=clobber)

Finally, we pass through any command line options for running the tool. In this case we are telling openroad to execute the script with -no_init option and to exit the from the program after the TCL file has been executed::

  chip.set('eda', tool, step, index, 'option', 'cmdline', option, clobber=clobber)

We have set the clobber=False for these commands because this code gets called at time of execuction and we want to have earlier user entered configuration to have priority.


The def_setup() function starts a handoff point from the SC schema to the TCL reference flow needed to drive openroad. The second aspect of the handoff is the sc_manifest.tcl file which is TCL based nested dictionary representation of teh SC schema dumped to file for every step and index in a compilation flow. A snippet of the file is shown belpw.


.. code-block:: tcl

   dict set sc_cfg asic targetlib [list  NangateOpenCellLibrary ]
   dict set sc_cfg scversion [list  0.0.1 ]
   dict set sc_cfg version [list  false ]
   dict set sc_cfg flowgraph import nproc [list  1 ]
   dict set sc_cfg flowgraph import input [list  source ]

With the sc_manifest.tcl file setting up all the SC parameters, all that is left is to access the sc_manifest.tcl dictionaries to drive the native openroad commands in TCL.

.. code-block:: tcl

  source ./sc_manifest.tcl

  #....
  set sc_mainlib     [lindex [dict get $sc_cfg asic targetlib] 0]
  set sc_libtype     [dict get $sc_cfg library $sc_mainlib arch]
  set sc_stackup     [dict get $sc_cfg asic stackup]
  set sc_techlef     [dict get $sc_cfg pdk aprtech $sc_stackup $sc_libtype lef]
  #...

  read_lef  $sc_techlef
  foreach lib $sc_targetlibs {
	read_lef [dict get $sc_cfg library $lib lef]
 }
