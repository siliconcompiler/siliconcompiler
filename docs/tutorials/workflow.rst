Python workflow
=======================

.. image:: _images/asicflow.png

This tutorial walks you through the basics of the SiliconCompiler ("SC")
project to teach you how to:

* Use the 'siliconcompiler' Python module
* Set up your design
* Load a technology target
* Create up a custom compilation flow
* Run a flow
* Report run metrics
  
Before reading this tutorial, you should know a bit of Python. A good entry
point is the official `Python tutorial
<https://docs.python.org/dev/tutorial/index.html>`_.

To run this tutorial you will need to have the siliconcompiler Python package a
nd its dependancies installed. Too check the installation version, enter sc
from your environment shell and check the only thing returned is a version
number. (your version number may vary depending on which version of SC you are running). If you anything else, something is wrong and you will need to check
your installation.

.. code-block:: bash
		
  $ sc -version
  0.0.1

  
Basics
------------------
To access SC first import the siliconcompiler module as follows::

  import siliconcmopiler

The first step to working with SC is to instantiate the SC class into an object as follows::

  chip = siliconcompiler.Chip(design="oh_add")

The above command sets the name of the design and loads the default SC default configuration schema, giving you direct acess to hundreds of configuration parameters. All SC parameters can be accessed through the set/get/add functions associed with the SC object. Let's observe the access methods in action, by fetching and printing out the SC version number::

  print(chip.get('version'))

If you are doing this from the Python REPL, the version printed should match up with the version reported from the 'sc' command line utlity.

Now let's set up the actual design::
  
  chip.add('source', 'examples/gcd/gcd.v')
  chip.set('asic', 'diearea', [(0,0), (100.13,100.8)])
  chip.set('asic', 'corearea', [(10.07,11.2),(90.25,91)])

For a single file basic design that's all you need! The source parameter is a list, so you can add as many files as you wish. For complex SoC designs, you make want to consider using the standard verilog design switches (-y, -I, -v,...) which are all supported in SC.

The 'diearea' and 'corearea' define the chip design area and legal placement area. For more information about floorplanning, see the ZeroSOC tutorial. In this case, we are auto-generating a basic floorplan using a list of (X,Y) tuples that defined the lower left and upper right corner of the rectangle.

Next, let's set a global parameters to show how the executuion flow can be
controlled::

  chip.set('quiet', True)

This parameter tells the SC run() command to pipe all messages to a file rather than to the primary display. EDA print A LOT! of information to STDOUT. By using the quiet parameter, it will be easier to follow what's going on. If you are
curious about gory details of the EDA tools, you can always see the full logfiles in <build_dir>/<design>/<jobname><jobid>/<step>/<tool>.log.

Targets
------------------
Modern process PDKs and EDA flows are incredibly complex with thousands of parameter settings and hundreds of data files read from disk. To make life easier for the designer it's important that we have the ability to encapsilate and abstract that information. Within the SC project, this encapsulation is done using the targtet() function, which loads a technology target and EDA flow based on a named target string. The eda flow and technology targets are dynamically loaded at runtime based on 'target' string specifed as <technology>_<edaflow>. The edaflow part of the string is optional and in this tutorial we will actually be defining a flow from scratch.

For this tutorial, we will load the freepdk45 PDK, which is a basic virtual (non manufacturable) PDK that includes technology setup and complete standard cell library::

  chip.target("freepdk45", loglevel="DEBUG")

In the above command we introduce a new concept, the "loglevel". The SC project
uses a unified Python logger object to display all important info, warning, error, and debug information. By setting the loglevel to "DEBUG" we will get more insight into what's going on under the hood with the target() function.

.. code-block:: console

  | DEBUG   | 2021-09-02 14:44:54 |     root     | Setting [pdk,foundry] to virtual
  | DEBUG   | 2021-09-02 14:44:54 |     root     | Setting [pdk,process] to freepdk45
  | DEBUG   | 2021-09-02 14:44:54 |     root     | Setting [pdk,node] to 45
  | DEBUG   | 2021-09-02 14:44:54 |     root     | Setting [pdk,version] to r1p0
  | DEBUG   | 2021-09-02 14:44:54 |     root     | Setting [pdk,stackup] to 10M
  | DEBUG   | 2021-09-02 14:44:54 |     root     | Setting [pdk,wafersize] to 300
  | DEBUG   | 2021-09-02 14:44:54 |     root     | Setting [pdk,edgemargin] to 2
  | DEBUG   | 2021-09-02 14:44:54 |     root     | Setting [pdk,hscribe] to 0.1
  | DEBUG   | 2021-09-02 14:44:54 |     root     | Setting [pdk,vscribe] to 0.1
  | DEBUG   | 2021-09-02 14:44:54 |     root     | Setting [pdk,d0] to 1.25
  | DEBUG   | 2021-09-02 14:44:54 |     root     | Setting [pdk,tapmax] to 120
  | DEBUG   | 2021-09-02 14:44:54 |     root     | Setting [pdk,tapoffset] to 0
  | DEBUG   | 2021-09-02 14:44:54 |     root     | Setting [pdk,aprtech,10M,10t,lef] to third_party/foundry/virtual/freepdk45/pdk/r1p0/apr/freepdk45.tech.lef


Flows
------------------

It's time to set up our custom ASIC compilation flow! First let's create a regular Python list that will define an ordered sequence of steps that we want to execute:: 
 
  flowpipe = ['import', 'syn', 'floorplan', 'place', 'cts', 'route', 'dfm', 'export']

The SC step names can be any legal non-reserved string, but they must match up with step names
used by the EDA tools accessed in the run() command. In this turtorial we will be using setup
scripts for Yosys, Klayout, and OpenROAD that make use of the above list of names.

Next we will use the list to create an execution graph for SC. The SC graph defines input/output dependancies within the flow, effectively defining which parts of the flow can run in parallel and which parts have to ru sequentially::

  for i, step in enumerate(flowpipe):
  
      chip.set('flowgraph', step, 'nproc',  1)

      chip.set('flowgraph', step, 'weight',  'cellarea', 1.0)
      chip.set('flowgraph', step, 'weight',  'peakpower', 1.0)
      chip.set('flowgraph', step, 'weight',  'standbypower', 1.0)

      for index in range(chip.get('flowgraph', step, 'nproc')):
          chip.set('metric', step, str(index), 'drv', 'goal', 0.0)
          chip.set('metric', step, str(index), 'holdwns', 'goal', 0.0)
          chip.set('metric', step, str(index), 'holdtns', 'goal', 0.0)
          chip.set('metric', step, str(index), 'setupwns', 'goal', 0.0)
          chip.set('metric', step, str(index), 'setuptns', 'goal', 0.0)
      
      if i > 0:
          chip.add('flowgraph', flowpipe[i], 'input',  flowpipe[i-1])
      else:
          chip.set('flowgraph', flowpipe[i], 'input',  'source')
	  

There is a for amount of cool stuff in the above code to unpack!

1. We iterate over all steps in the flowpipe in order::
  
     for i, step in enumerate(flowpipe):

2. We set the number of unique design experiments to run in parallel for a step.::
     
    chip.set('flowgraph', step, 'nproc',  1)

3. We set up the weights on a per step basis to let us calculate the winning experiment within a step using the SC minimum() fuction. Metrics with undefined weight values (None) values are ignored during minimum() calcuations. For a complete set of metrics, see the schema reference manual.::

    chip.set('flowgraph', step, 'weight',  'cellarea', 1.0)
    chip.set('flowgraph', step, 'weight',  'peakpower', 1.0)
    chip.set('flowgraph', step, 'weight',  'standbypower', 1.0)

4. We set the hard goals that the compilation must meet. Metrics without goals are unconstrained are not used in minimuk score calculations. In this example, we asert a number of hard metrics for timing and design rules that must be met.::

    chip.set('metric', step, str(index), 'drv', 'goal', 0.0)
    chip.set('metric', step, str(index), 'holdwns', 'goal', 0.0)
    chip.set('metric', step, str(index), 'holdtns', 'goal', 0.0)
    chip.set('metric', step, str(index), 'setupwns', 'goal', 0.0)
    chip.set('metric', step, str(index), 'setuptns', 'goal', 0.0)
    
5. Finally we set up the execution depeendnacy pipeline, but stating that all steps except for the first one gets its inputs from the previous step in the flowpipe. The first step in the pipeline reads static sources from the file system and useds 'source' as a keyword::
     
    if i > 0:
      chip.add('flowgraph', flowpipe[i], 'input',  flowpipe[i-1])
    else:
      chip.set('flowgraph', flowpipe[i], 'input',  'source')


Execution
------------------


