.. _custom_flow_tutorial:

##########################
Authoring a Custom Flow
##########################

The built-in flows cover the usual paths -- lint, synthesis, RTL-to-GDSII,
signoff. Sooner or later you want something they do not do: an extra check
between two steps, a tool the standard flow does not run, or a pipeline
assembled out of pieces of several flows.

A :term:`flow` is just a graph of tasks, and building one is a handful of lines.
This page walks one end to end; :ref:`Building a Flowgraph <dev_flows>` is the
API reference to keep open beside it.

When you actually need one
==========================

Reach for a custom flow last, not first. Three cheaper things handle most cases:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - You want to
     - Do this instead
   * - Run only part of a standard flow
     - :keypath:`option,from` / :keypath:`option,to` --
       :ref:`Run only part of the flow <howto>`
   * - Try several settings for one step
     - the flow's ``_np`` argument --
       :ref:`Parallel Job Execution <parallel_execution>`
   * - Inject a Tcl script around a tool
     - :meth:`~.Task.add_prescript` / :meth:`~.Task.add_postscript` --
       :ref:`Using Commercial Tools <commercial_tools>`
   * - **Change which tools run, or in what order**
     - **a custom flow**

Nodes and edges
===============

Two calls build a graph. :meth:`.Flowgraph.node` names a :term:`step` and gives
it a task to run; :meth:`.Flowgraph.edge` says one must finish before another
starts:

.. code-block:: python

   from siliconcompiler import Flowgraph

   flow = Flowgraph("myflow")
   flow.node("import", ImportFilesTask())
   flow.node("synthesis", SynthesisTask())
   flow.edge("import", "synthesis")

   project.set_flow(flow)

Each node is a :term:`task` -- a tool driver class, not a tool name. That is what
lets a flow be checked before anything runs: the task knows what it needs and
what it produces.

Nodes with no edge between them carry no ordering constraint, so the scheduler
*may* run them together. Whether it does depends on
:keypath:`option,scheduler,maxnodes`, the resources available, and how wide the
rest of the flow is -- leaving an edge out permits concurrency rather than
guaranteeing it.

A worked example
================

``examples/heartbeat`` builds a timing-signoff flow that no built-in flow
provides: stage a parasitics file into a node's inputs, then run timing against
it.

.. literalinclude:: examples/heartbeat/make.py
   :language: python
   :start-after: signoff_flow = Flowgraph("timingsignoff")
   :end-before: signoff.option.set_jobname
   :dedent: 4

Two nodes, one edge, and it replaces the flow the target installed. Note what is
*not* here: the target is still loaded, so the PDK, the libraries and the delay
models all come from it. A custom flow changes what runs, not what it runs
against.

The rest of that function is worth reading for how a custom flow fits into a
larger build -- it is the third job in a chain, taking a netlist from the
implementation run and a VCD from a simulation run. See
:ref:`Multi-Job Flows <multi_job_flows>` for that pattern.

Configuring a task in the flow
==============================

Once a task is in a flow, :meth:`~.Task.find_task` reaches it to set its options:

.. code-block:: python

   ImportFilesTask.find_task(signoff).add_import_file(spef)

This is the general shape for tuning any node: find the task on the project, then
call its accessors. It works for built-in flows too --
``SynthesisTask.find_task(project).set_threads(4)``.

Reusing pieces
==============

Flows compose. :meth:`.Flowgraph.graph` splices an existing flow in as a
subgraph, which is how the built-in flows are built out of each other -- the ASIC
flow is a floorplanning flow, a placement flow, a routing flow and more, joined
together:

.. code-block:: python

   flow = Flowgraph("check_then_build")
   flow.graph(LintFlow(), name="lint")
   flow.graph(SynthesisFlow(), name="syn")

Prefer this to rebuilding a standard pipeline node by node -- you inherit its
updates for free.

Checking what you built
=======================

A flowgraph is data, so look at it before you spend an hour running it:

.. code-block:: python

   flow.write_flowgraph("myflow.svg")

.. warning::
   Give a new flow its own **name**. A :ref:`target <builtin_targets>` has usually
   already registered a flow under the default one, and constructing another with
   that name resolves back to *its* copy -- so your changes silently do not
   appear. The failure is quiet: the run succeeds, just not the run you wrote.

:meth:`.Project.run` checks the graph for correctness before executing anything:
unreachable nodes, missing inputs, and tasks whose requirements are not met all
fail before a tool starts.

Writing the task itself
=======================

If no existing task wraps the tool you need, that is the next layer down:
:ref:`Building a Tool <dev_tools>` covers writing a driver -- the setup, the
command line, and reading metrics back out of the tool's reports. The four
methods a task can implement are :meth:`~.Task.setup`, :meth:`~.Task.pre_process`,
:meth:`~.Task.runtime_options` and :meth:`~.Task.post_process`.

.. seealso::
   :ref:`Building a Flowgraph <dev_flows>` for the full API,
   :ref:`Compilation Process <execution_model>` for how a graph is executed, and
   :ref:`flows <builtin_flows>` for the built-in ones -- worth reading as
   worked examples before writing your own.
