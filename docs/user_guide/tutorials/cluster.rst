.. _cluster_tutorial:

##########################
Running on a Cluster
##########################

A flowgraph is a set of independent tasks with declared dependencies, which is
exactly the shape a job scheduler wants. Handing the nodes to a cluster instead
of running them on your laptop is one option:

.. code-block:: python

   project.option.scheduler.set_name("slurm")

Everything else -- the design, the flow, the target -- is unchanged. The same
script runs locally, on a cluster, or in containers.

What the schedulers are
=======================

.. list-table::
   :header-rows: 1
   :widths: 18 82

   * - Value
     - Runs each node
   * - *(unset)*
     - As a process on the machine you launched from. The default.
   * - ``slurm``
     - As a Slurm job. Needs a reachable ``slurmctld``.
   * - ``docker``
     - In its own container -- see :ref:`Docker <docker_two_ways>`

.. note::
   ``lsf`` and ``sge`` are accepted by the schema but **have no implementation**
   -- only ``slurm`` and ``docker`` are dispatched. Setting either currently
   falls through to running locally. If you need one of them, say so on
   `Discussions <https://github.com/siliconcompiler/siliconcompiler/discussions>`_;
   the dispatch layer is small and the Slurm one is the template.

.. important::
   **The build directory must be on shared storage.** Nodes pass results to each
   other through ``build/``, so every host that might run a node has to see the
   same filesystem at the same path. This is the single most common reason a
   working local build fails on a cluster.

   .. code-block:: python

      project.option.set_builddir("/shared/scratch/me/build")

Asking for resources
====================

Per-node resource requests translate to the scheduler's own switches:

.. code-block:: python

   project.option.scheduler.set_cores(16)
   project.option.scheduler.set_memory(64000)      # MB
   project.option.scheduler.set_queue("bigmem")    # partition

All three take ``step=``/``index=``, which is usually what you want -- routing
needs a different machine than linting does:

.. code-block:: python

   project.option.scheduler.set_cores(32, step="route")
   project.option.scheduler.set_memory(128000, step="route")

Anything the accessors do not cover goes through
:meth:`~.SchedulerSchema.add_options`, which passes switches to the scheduler
verbatim.

Bounding the fan-out
====================

On a cluster the limit stops being your core count and starts being what you are
allowed to occupy:

.. code-block:: python

   project.option.scheduler.set_maxnodes(50)    # concurrent nodes
   project.option.scheduler.set_maxthreads(8)   # threads per tool

These compose with the flow's own width. A sweep of 10 jobs, each with
``syn_np=4``, is 40 concurrent tool invocations before either of these applies --
see :ref:`Parallel Job Execution <parallel_execution>`, which is worth reading
first if you are about to point this at a shared machine.

Being told when it finishes
===========================

A cluster run is one you walk away from:

.. code-block:: python

   project.option.scheduler.add_msgcontact("me@example.com")
   project.option.scheduler.add_msgevent("end")     # also: "begin", "timeout", "fail"

:ref:`Job status emails <emails>` covers what arrives.

Submitting without waiting
==========================

:meth:`~.SchedulerSchema.set_defer` submits the work and returns rather than
blocking until it completes -- for jobs longer than the session you are willing
to keep open.

Setting up Slurm
================

If you do not already have a cluster, :ref:`Slurm setup <slurmsetup>` walks
through configuring a single machine as a one-host cluster, which is the right
way to test that a script works under a scheduler before asking for real
resources. Add hosts afterwards.

.. seealso::
   :ref:`Remote processing <remote_processing>` is the other way to run
   elsewhere -- a SiliconCompiler server rather than a batch scheduler, and no
   shared filesystem required. :ref:`Docker <docker>` runs the tools locally
   without installing them.
