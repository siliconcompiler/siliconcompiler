Execution model
===================================

The SiliconCompiler execution model is built around the concept of a
`flowgraph <https://en.wikipedia.org/wiki/Flow_graph>`_. Each hardware compilation
is performed based on a static graph with compilation steps and input/output
relationships defined by the user. The compilation flow specification is captured in
the 'flowgraph' schema dictionary.

Setting up a compilation flowgraph involves setting the following parameters in the
SC schema:

  1. Associating a set of named steps with tools or built in SC functions ("nodes").
  2. Connecting inputs and outputs of steps togeteher to create sequence ("edge").
  3. Optionally assign a set of weights to metrics for each step.
  4. Optionally define how many parallel indices to run for each step.

Once the flowgraph has been created, compilation is performed using the SC run()
function. The run() function runs through the complete flowgraph from start to
finish, respecting the users specified input/output relationships in the graph to
ensure ensure that execution is done in the correct order. Steps with input
dependancies are blocked from continuing until all inputs are ready.

The 'index' feature enables parallel execution of a step tool on the same data with
different configuration settings. For example, logical synthesis could be run on a
design with different options for flattening, partitionined, or buffer.

All individual compilation operations stored in individual direrctories, with all
inputs and outputs self-contained within those directories. The directory structure
of a design is shown below.

<build_dir>/<design>/<jobname>/<step>/<index>

Communication between steps is done through file in the inputs/outputs directories:

* **step input files**: <build_dir>/<design>/<jobname>/<step>/<index>/inputs
* **step output files**: <build_dir>/<design>/<jobname>/<step>/<index>/outputs

At the end of each run() call, the current in memory job manifest is copied into a
job history which can be accessed by the user to to create sophisticated non-linear
flows that take into account run history and gradients. The code snippet below shows
a minimal sequence leveraging the multi-job feature.::

  chip.run()
  chip.set('jobname', 'newname')
  #chip.set('some parameter..')
  chip.run()


The followinig examples illustrate a number of compilation flows supported by SC.

Serial pipelines
----------------

Serial compilation flows like those traditionally seen in make files and EDA TCL
reference scripts can be easily ported to SC by setting up a a flowgraph with a
set of steps where the output of one step is connected to the input of the next
step. Each step is set up with an single index ('0'). The code snippet and
diagram below illustrates the creation of a serial pipeline::


  # setting up tools
  chip.set('flowgraph', 'import', '0', 'tool', 'surelog')
  chip.set('flowgraph', 'syn', '0', 'tool', 'yosys')
  chip.set('flowgraph', 'apr', '0', 'tool', 'openroad')
  chip.set('flowgraph', 'export', '0', 'tool', 'klayout')

  # defining intput/output relationship
  chip.add('flowgraph', 'syn', '0', 'input', 'import0')
  chip.add('flowgraph', 'apr', '0', 'input', 'syn0')
  chip.add('flowgraph', 'export', '0', 'input', 'apr0')

.. image:: ../_images/serial.png

Fork-join pattern
------------------
The ubiqurous fork join execution pattern can be created in SC by adding steps
associated with built in function steps to the flowgraph. Built in step_minimum()
and step_maximum() functions operate on the recorded metrics of the step/index
under consideration. Collecting outputs from multiple orthogonal steps can be
donie through the step_join() function. Steps requiring inputs from multiple input
steps are blocked until all intputs from all inputs steps are available.

.. image:: ../_images/forkjoin.png

Parallel pipelines
-------------------
Parallel pipelines is another common pattern found in parallel programming. It's
especially useful for embarrasingly parallel applications such as cosntrained
random verification and brute force search design of experiments. SiliconCompiler
emables parallel pipelines by: 1) supporting any any step/index output to any
step/index input within the flowgraph and by 2.) Inclusion of built-in join
functions suchc as step_join() and step_assert(). The example below shows a place
and route experiment that imports source files, runs 4 separate sets of
experiments on the same data, and then picks the best one based on the metrics
reported and metrics weights set in the flowgraph.

.. image:: ../_images/pipes.png

Iterative flows
-----------------

More complex iterative comilation flows can be created through the creation of
Python programs that 1.) calls run() multiple times using a different jobname and a the 'steplist' to select a subset of the flowgraph. 2.) writes Python logic to query the per job metrics to control the compilation flow decision.

.. image:: ../_images/complex.png
