ASIC Workflow
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


Pre-requisites
------------------

Before reading this tutorial, you should know a bit of Python. A good entry
point is the official `Python tutorial
<https://docs.python.org/dev/tutorial/index.html>`_.

You will also need to have the siliconcompiler Python package installed.
If you are running locally, you will also require an up to date installation of all the
EDA tools (verilator, yosys,  openroad, and klayout). Too check the SC installation version,
enter sc from your environment shell and check the only thing returned is a version
number. (your version number may vary depending on which version of SC you are running).
If you see anything else, something is wrong and you will need to check your installation.

.. code-block:: console

  $ sc -version
  0.0.1


To check that you are ready for local execution:

.. code-block:: console

  $ sc third_party/designs/oh/stdlib/hdl/oh_add.v -remote_addr siliconc-asic_diearea -asic_corearea -design oh_add -quiet -relax

If you have access to a remote try the same commmand with the -remote_addr <SERVER>, where server is an IP address that accepts SC
requests (eg. server.siliconcompiler.com).

.. code-block:: console

  $ SC_SERVER="server.siliconcompiler.com"
  sc third_party/designs/oh/stdlib/hdl/oh_add.v -asic_diearea -asic_corearea -design oh_add -quiet -relax -remote_addr $SC_SERVER

Basics
------------------

For this tutorial, we recommend starting Python (3.x) in interactive mode

.. code-block:: console

  $ python3.9
  Python 3.9 (default, June 4 2019, 09:25:04)
  [GCC 4.8.2] on linux
  Type "help", "copyright", "credits" or "license" for more information.
  >>>

To access SC first import the siliconcompiler module::

  >>> import siliconcompiler

The first step to working with SC is to instantiate the SC class into an objects::

  >>> chip = siliconcompiler.Chip(design="oh_add")

The above command sets the name of the design and loads the default SC default configuration schema, giving you direct acess to hundreds of configuration parameters. All SC parameters can be accessed through the set/get/add functions associed with the SC object. Let's observe the access methods in action, by fetching and printing out the SC version number::

  >>> print(chip.get('scversion'))

The version printed should match up with the version reported from the 'sc' command line utlity.

Now let's set up the actual design!::

  >>> chip.add('source', 'examples/gcd/gcd.v')
  >>> chip.set('asic', 'diearea', [(0,0), (100.13,100.8)])
  >>> chip.set('asic', 'corearea', [(10.07,11.2),(90.25,91)])

For a single file basic design that's all you need! The source parameter is a list, so you can add as many files as you wish. For complex SoC designs, you make want to consider using the standard verilog design switches (-y, -I, -v,...) which are all supported in SC.

The 'diearea' and 'corearea' define the chip design area and legal placement area. For more information about floorplanning, see the ZeroSOC tutorial. In this case, we are auto-generating a basic floorplan using a list of (X,Y) tuples that defined the lower left and upper right corner of the rectangle.

Next, let's set a global parameters to show how the executuion flow can be
controlled::

  >>> chip.set('quiet', True)

This parameter tells the SC run() command to pipe all messages to a file rather than to the primary display. EDA print A LOT! of information to STDOUT. By using the quiet parameter, it will be easier to follow what's going on. If you are
curious about gory details of the EDA tools, you can always see the full logfiles in <build_dir>/<design>/<jobname><jobid>/<step>/<tool>.log.

Targets
------------------
Modern process PDKs and EDA flows are incredibly complex with thousands of parameter settings and hundreds of data files read from disk. To make life easier for the designer it's important that we have the ability to encapsilate and abstract that information. Within the SC project, this encapsulation is done using the targtet() function, which loads a technology target and EDA flow based on a named target string. The eda flow and technology targets are dynamically loaded at runtime based on 'target' string specifed as <technology>_<edaflow>. The edaflow part of the string is optional and in this tutorial we will actually be defining a flow from scratch.

For this tutorial, we will load the freepdk45 PDK, which is a basic virtual (non manufacturable) PDK that includes technology setup and complete standard cell library::

  >>> chip.target("freepdk45")

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

  >>> flowpipe = ['import', 'syn', 'floorplan', 'place', 'cts', 'route', 'dfm', 'export']

The SC step names can be any legal non-reserved string, but they must match up with step names
used by the EDA tools accessed in the run() command. In this turtorial we will be using setup
scripts for Yosys, Klayout, and OpenROAD that make use of the above list of names.

Next we will use the list to create an execution graph for SC. The SC graph defines input/output dependancies within the flow, effectively defining which parts of the flow can run in parallel and which parts have to run sequentially. Copy past the block of code in theo the Python interpreter making sure to start the copy block at the with the for (with no leading space) and pressing enter an extra time in the interpreter::

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

EDA Setup
---------------

We have now set up the basic execution flow and metrics, but we haven't specified which tools to use for each step. In the below code, we connect execution stepss with specific tools.::

  for step in flowpipe:
      if step == 'import':
          tool = 'verilator'
      elif step == 'syn':
          tool = 'yosys'
      elif step == 'export':
          tool = 'klayout'
      else:
          tool = 'openroad'
      chip.set('flowgraph', step, 'tool', tool)

The 'magic' of setting up these tools happens at runtime when calling the run() function, at which point point the <tool>.py module is loaded and a a fixed name function "setup_tool()" is exeucted. The setup of these tools is beyond the scope o this tutorial, but if you curious about the process, you can take a look at one of the setup files here. [TODO: Add link]


Check
------------------



Execution
------------------
We are now ready to execute the flow we defined::

    chip.run()

That's it! The console output should look something like the trace below. You can observe each tool being et up sequentually after which processes are forked for each step. Steps with input dependancies wait until all inputs are ready before strating execution.

.. code-block:: console

  | INFO    | 2021-09-02 15:56:31 |     root     | Setting up tool 'verilator' in step 'import'
  | INFO    | 2021-09-02 15:56:31 |     root     | Setting up tool 'yosys' in step 'syn'
  | INFO    | 2021-09-02 15:56:31 |     root     | Setting up tool 'openroad' in step 'floorplan'
  | INFO    | 2021-09-02 15:56:31 |     root     | Setting up tool 'openroad' in step 'synopt'
  | INFO    | 2021-09-02 15:56:31 |     root     | Setting up tool 'openroad' in step 'place'
  | INFO    | 2021-09-02 15:56:31 |     root     | Setting up tool 'openroad' in step 'cts'
  | INFO    | 2021-09-02 15:56:31 |     root     | Setting up tool 'openroad' in step 'route'
  | INFO    | 2021-09-02 15:56:31 |     root     | Setting up tool 'openroad' in step 'dfm'
  | INFO    | 2021-09-02 15:56:31 |     root     | Setting up tool 'klayout' in step 'export'
  | INFO    | 2021-09-02 15:56:31 |     root     | Computing file hashes with hashmode=OFF
  | INFO    | 2021-09-02 15:56:31 |     root     | Step 'import' waiting on inputs
  | INFO    | 2021-09-02 15:56:31 |     root     | Step 'syn' waiting on inputs
  | INFO    | 2021-09-02 15:56:31 |     root     | Step 'floorplan' waiting on inputs
  | INFO    | 2021-09-02 15:56:31 |     root     | Step 'synopt' waiting on inputs
  | INFO    | 2021-09-02 15:56:31 |     root     | Step 'place' waiting on inputs
  | INFO    | 2021-09-02 15:56:31 |     root     | Step 'dfm' waiting on inputs
  | INFO    | 2021-09-02 15:56:31 |     root     | Step 'export' waiting on inputs
  | INFO    | 2021-09-02 15:56:31 |     root     | Step 'route' waiting on inputs
  | INFO    | 2021-09-02 15:56:31 |     root     | Step 'cts' waiting on inputs
  | INFO    | 2021-09-02 15:56:31 |     root     | Running import in /home/aolofsson//build/gcd/job0/import0


Metrics
------------------
Unless there was an ERROR printed to the STDERR, the run shuld have finished and we should now be able to view files and see metrics.
As a simple example, to get the cell area after synthesis, simply get the parameter for the associated step and index. THe index refers to an individual thread/process within a step. Until now, all steps have only had one thread per step, so the index is zero::

  print(chip.get('metric', 'syn', str(0), 'cellarea', 'real')

To get a complete summary of the run from start to finish, we can use the summary function::

  chip.summary()


The console output should look something like the following.

.. code-block:: console

  SUMMARY:

  design = gcd
  foundry = virtual
  process = freepdk45
  targetlibs = NangateOpenCellLibrary
  jobdir = build/gcd/job0

                  import0      syn0   floorplan0   synopt0     place0      cts0      route0      dfm0     export0
  errors            0          0          1          1          1          1          1          1          0
  warnings          0          72         1          0          2          3          4          0          0
  drv               0          0          0          0          0          0          0          0          0
  cellarea         0.0       413.63     414.0      414.0      490.0      499.0       0.0       499.0       0.0
  peakpower        0.0        0.0      0.000188   0.000188   0.000206   0.000279     0.0      0.000292     0.0
  standbypower     0.0        0.0      8.62e-06   8.62e-06   1.13e-05   1.17e-05     0.0      1.17e-05     0.0
  holdwns          0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
  holdtns          0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
  setupwns         0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
  setuptns         0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
  registers         0          0          0          0          0          0          0          0          0
  cells             0         249         0          0          0          0          0          0          0
  rambits           0          0          0          0          0          0          0          0          0
  xtors             0          0          0          0          0          0          0          0          0
  nets              0          0          0          0          0          0          0          0          0
  pins              0          0          0          0          0          0          0          0          0
  vias              0          0          0          0          0          0         2093        0          0
  wirelength       0.0        0.0        0.0        0.0        0.0        0.0       6251.0      0.0        0.0
  overflow          0          0          0          0          0          0          0          0          0
  density          0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
  runtime          0.16       0.82       1.02       1.12       1.53       2.99       5.83       1.0        0.9
  memory           0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
  --------------------------------------------------------------------------------------------------------------


Show
------------------

Based on the results, it looks like we have a viable design, but twe still haven't seen any polygons. To display the layout, we use the show() method together with the filename. Note that technology specific layer defintions and dispaly settings are all set up "automagically' thanks to the target() function::


  gdsfile = "build_dir/oh_add/job0/export0/output/oh_add.gds"
  chip.show(gdsfile)

If things worked out, you should see something like the image below pop-up. In this tutorual we conigured SC to use klayout for gds viewing.

.. image:: _images/kalyout_workflow.png


Extra Credit
------------------

Up to now, hopefully you have seen that SC is a simple but powerful framework for configuring automated ASIC compilation flows. Still, we have left the best part for last!  As mentioned earlier, modern process PDKs and EDA tools are incredibly complex and generally requires months of experimentation to tune them for best performance. To make matters more complicated, the optimal settigs for the process/tool combination may be design specific, meaning that the optimal settings for one type of design may be suboptimal for a different design.

As a simple illustrative example, consider the placement_density variale for OpenRoad. Each technology node supported by the OpenROAD platform has a slightly different setting for this variable, but it's not clear that the value chosen is ideal for all designs being exercised at that node. With the small snipper of code below the run() function can cycle through the whole range of possibilities to select the one that works best::

  N = 10
  chip.set('flowgraph','place','nproc',N)
  for index in range(N):
      chip.set('eda', 'openroad', 'place', str(index),
             'option', 'place_density', str(index*0.1))

  chip.run()
  chip.summary()

One of the coolest features of SC is that all of the indices withina a step are run in parallel, so if you are runnign on a parallel machine, you get close to strong scaling up to the number of physical CPU cores (or servers) available!  Once all the indices have completed, a minimum() function is called under the hood to select the best index from the lot to use for the next step in the exeuction grap. Some indices will fail, but that's ok: we only need one great to succeed for the input of the cts step. Below you can see the output from the chip.summary() call. In this case it wasn't a huge gain  because our design was small and simple, but it should give you an idea of what is possible. A clever person could easily extend the example above to sweep interesting tool settings for every step in the flowgraph to realize significant per design gais.;-)


.. code-block:: console

  SUMMARY:

  design = gcd
  foundry = virtual
  process = freepdk45
  targetlibs = NangateOpenCellLibrary
  jobdir = build/gcd/job0

                  import0      syn0   floorplan0   synopt0     place8      cts0      route0      dfm0     export0
  errors            0          0          1          1          1          1          1          1          0
  warnings          0          72         1          0          2          3          4          0          0
  drv               0          0          0          0          0          0          0          0          0
  cellarea         0.0       413.63     414.0      414.0      490.0      499.0       0.0       499.0       0.0
  peakpower        0.0        0.0      0.000188   0.000188   0.000206   0.000279     0.0      0.000292     0.0
  standbypower     0.0        0.0      8.62e-06   8.62e-06   1.13e-05   1.17e-05     0.0      1.17e-05     0.0
  holdwns          0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
  holdtns          0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
  setupwns         0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
  setuptns         0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
  registers         0          0          0          0          0          0          0          0          0
  cells             0         249         0          0          0          0          0          0          0
  rambits           0          0          0          0          0          0          0          0          0
  xtors             0          0          0          0          0          0          0          0          0
  nets              0          0          0          0          0          0          0          0          0
  pins              0          0          0          0          0          0          0          0          0
  vias              0          0          0          0          0          0         2093        0          0
  wirelength       0.0        0.0        0.0        0.0        0.0        0.0       6251.0      0.0        0.0
  overflow          0          0          0          0          0          0          0          0          0
  density          0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
  runtime          0.16       0.82       1.02       1.12       1.53       2.99       5.83       1.0        0.9
  memory           0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
  --------------------------------------------------------------------------------------------------------------


Conclusion
------------------
Awesome! You made it through the SC workflow tutorial. Hopefully, you have seen how simple yet powerful the SC approach is.

Good luck!
