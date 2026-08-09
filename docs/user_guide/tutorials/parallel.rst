.. _parallel_execution:

######################
Parallel Job Execution
######################

Single-threaded performance has saturated, so making hardware compilation fast
means making effective use of parallel hardware. Two things work in our favour:
the compute-to-data ratio of the expensive compilation steps is high, and several
of those steps partition into embarrassingly parallel problems.

This tutorial runs one workload three ways -- synthesizing the same adder at four
datawidths -- and shows where the parallelism comes from in each. The code is a
single script:

* `examples/parallel/parallel.py <https://github.com/siliconcompiler/siliconcompiler/blob/main/examples/parallel/parallel.py>`_
* `examples/parallel/adder.v <https://github.com/siliconcompiler/siliconcompiler/blob/main/examples/parallel/adder.v>`_

.. code-block:: bash

   ./parallel.py serial
   ./parallel.py indexed
   ./parallel.py processes

Each prints its own wall-clock time, so the three are directly comparable on your
machine.

The Workload
============

One :class:`.Design` carries an ``rtl.<n>`` :term:`fileset` per datawidth, each
setting the Verilog parameter ``N``:

.. literalinclude:: examples/parallel/parallel.py
   :language: python
   :start-after: def make_design():
   :end-before: return design
   :dedent: 4

Nothing about this is specific to parallelism -- it is the same sweep-by-fileset
pattern used in :ref:`Multi-Job Flows <multi_job_flows>`.

Approach 1: Serial
==================

The baseline: each datawidth runs to completion before the next one starts, and
within a job only one :term:`flowgraph node` runs at a time.

.. graphviz:: _images/parallel/serial.dot
   :align: center

.. literalinclude:: examples/parallel/parallel.py
   :language: python
   :start-after: def run_serial():
   :end-before: # ------
   :dedent: 4

:keypath:`option,scheduler,maxnodes` is pinned to ``1`` here only to make the
baseline honest. Left alone it defaults to the number of available cores, so
**SiliconCompiler already overlaps independent nodes without you asking** -- the
serial case is the one you have to opt into.

Approach 2: Index Parallelism -- Inside a Job
=============================================

:term:`Indices <index>` are variants of a :term:`step` operating on identical
input data. They have no edges between them, so the scheduler is free to run them
concurrently, and a ``minimum`` node picks the best result.

.. graphviz:: _images/parallel/indexed.dot
   :align: center

Flows expose this through ``_np`` arguments -- ``syn_np`` here, and
``floorplan_np``, ``place_np``, ``cts_np``, ``route_np`` on
:ref:`asicflow <schema-siliconcompiler-flows-asicflow-asicflow>`:

.. literalinclude:: examples/parallel/parallel.py
   :language: python
   :start-after: def run_indexed():
   :end-before: # ------
   :dedent: 4

This is the approach to reach for when you want to *explore* -- several tool
configurations against the same input, with the winner selected automatically.
:ref:`Using Index for Optimization <using_index_for_opt>` builds a synthesis
sweep out of the same primitives.

.. warning::
   Give the flow its own ``name``. A :ref:`target <builtin_targets>` has usually
   already registered a flow under the default name, and constructing another
   with that name resolves back to *its* copy::

       project.set_flow(SynthesisFlow(syn_np=4))                 # silently syn_np=1
       project.set_flow(SynthesisFlow(name="sweep", syn_np=4))   # four indices

   The failure mode is quiet: the run succeeds, just without the extra indices.
   Check with ``project.get("flowgraph", project.option.get_flow(),
   field="schema").get_nodes()``.

Approach 3: Process Parallelism -- Across Jobs
==============================================

Index parallelism cannot help when the runs differ in their *inputs*: four
datawidths are four different elaborations, so they are four different flows.
Because they share nothing, they can run as independent processes.

.. graphviz:: _images/parallel/processes.dot
   :align: center

.. literalinclude:: examples/parallel/parallel.py
   :language: python
   :start-after: def run_processes():
   :end-before: APPROACHES
   :dedent: 4

The worker returns a metric rather than the project, because what crosses a
process boundary has to be picklable:

.. literalinclude:: examples/parallel/parallel.py
   :language: python
   :start-after: def _run_one(n):
   :end-before: def run_processes
   :dedent: 4

.. note::
   **Guard your script.** SiliconCompiler forks its own node workers on Linux,
   but a script that itself uses ``multiprocessing`` must be import-safe: on
   macOS and Windows the child re-imports the file, and without
   ``if __name__ == "__main__":`` it recurses instead of running.

Choosing Between Them
=====================

.. list-table::
   :header-rows: 1
   :widths: 22 39 39

   * - Approach
     - Use when
     - Bounded by
   * - **Index**
     - Runs share an input and differ in tool settings; you want the best result
       picked for you.
     - :keypath:`option,scheduler,maxnodes`, and the width the flow was built
       with (``_np``).
   * - **Process**
     - Runs differ in their inputs -- different designs, parameters, or targets
       -- and you want all the results.
     - Your pool size, and memory: each process holds a full toolchain.
   * - **Both**
     - A sweep where each point also explores settings.
     - Multiply the two; it is easy to oversubscribe.

The two compose, and that is where oversubscription starts: a pool of 4 processes
each running a flow with ``syn_np=4`` can ask for 16 concurrent tool invocations,
each of which may itself be multi-threaded. Bound it with
:keypath:`option,scheduler,maxnodes` and
:keypath:`option,scheduler,maxthreads` -- see
:ref:`Control how much of the machine a run uses <howto>`.

.. seealso::
   * :ref:`Compilation process <execution_model>` -- steps, indices, and how the
     flowgraph is executed.
   * :ref:`Multi-Job Flows <multi_job_flows>` -- chaining and sweeping jobs, and
     reading results back out of history.
   * :ref:`Remote processing <remote_processing>` -- moving the same flows onto a
     cluster, where the ceiling is much higher than one workstation.
