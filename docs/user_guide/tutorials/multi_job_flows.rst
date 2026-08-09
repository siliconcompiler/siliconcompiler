.. _multi_job_flows:

##############################
Multi-Job Flows and Automation
##############################

:ref:`Compilation process <execution_model>` describes setting up one job. This
tutorial covers what happens when one ``run()`` is not enough: chaining a second
flow onto the results of the first, sweeping a parameter across many jobs, and
building a design hierarchically.

All three rest on the same mechanism -- **job history** -- so it is worth
understanding that first.

Job History
===========

Every :meth:`.Project.run()` copies the finished project state into a history
record keyed by :keypath:`option,jobname`, and :meth:`.Project.history` reads it
back:

.. code-block:: python

   project.option.set_jobname("baseline")
   project.run()

   # Change something, or the second run just reproduces the first.
   project.option.set_optmode(3)             # optimize harder
   project.option.set_jobname("tuned")
   project.run()

   before = project.history("baseline").get("metric", "cellarea",
                                            step="synthesis", index="0")
   after = project.history("tuned").get("metric", "cellarea",
                                        step="synthesis", index="0")

Three properties of the record are worth knowing, because they decide how you
structure a script:

* **Keyed by jobname.** Give each run a distinct name or you cannot tell the
  results apart. Reusing one replaces the earlier record and logs
  ``Overwriting job <name>``.
* **Recorded even when the run fails.** The history is written in a ``finally``
  block, so a job that errored is still queryable -- which is what makes it
  usable for automation that has to cope with failures.
* **A full project, not just metrics.** ``history()`` returns a
  :class:`.Project`, so anything readable on a live project is readable on a
  past one.

.. _multi_job_chaining:

Pattern 1: Chaining Flows
=========================

Run one flow, then feed its outputs into another as inputs. The canonical case is
implementation followed by signoff, because they are different flows over the
same design.

.. graphviz:: _images/multi_job/chaining.dot
   :align: center

:meth:`.Project.find_result` locates an output by extension and step, which is
what lets the second job pick up where the first left off:

.. literalinclude:: examples/gcd/gcd_skywater.py
   :language: python
   :start-after: # --- Part 2: Standalone LVS and DRC Verification ---
   :end-before: # Print a summary of the signoff results.
   :dedent: 4

Note the three moving parts: a **new fileset** holding the previous job's
outputs, ``clobber=True`` so it replaces rather than appends on a re-run, and a
**new jobname** so the signoff results do not overwrite the implementation
record.

Full example:
`examples/gcd/gcd_skywater.py <https://github.com/siliconcompiler/siliconcompiler/blob/main/examples/gcd/gcd_skywater.py>`_.

.. _multi_job_sweep:

Pattern 2: Sweeping a Parameter
===============================

Run the same flow many times with one thing changed, then compare.

.. graphviz:: _images/multi_job/sweep.dot
   :align: center

Carry each variant as its own :term:`fileset` and give each run its own jobname:

.. literalinclude:: examples/oh_experiments/adder_sweep.py
   :language: python
   :start-after: # Loop through the data widths again, this time to run the synthesis flow for each one.
   :end-before: # --- Plotting and Reporting Results ---
   :dedent: 4

The loop body is the whole pattern: swap the fileset, name the job, run, read the
metric back out of history.

Full example:
`examples/oh_experiments/adder_sweep.py <https://github.com/siliconcompiler/siliconcompiler/blob/main/examples/oh_experiments/adder_sweep.py>`_.
`check_area.py <https://github.com/siliconcompiler/siliconcompiler/blob/main/examples/oh_experiments/check_area.py>`_
in the same directory is the variant that builds a **fresh project per run**
instead of reusing one -- worth preferring when the runs differ in more than one
setting, since it removes any chance of state leaking between them.

.. seealso::
   Sweeps are also the natural place to add parallelism: the jobs are
   independent, so they can run at the same time.
   :ref:`Parallel Job Execution <parallel_execution>` covers how.

.. _multi_job_hierarchical:

Pattern 3: Hierarchical Builds
==============================

Build a block in one job, then consume its results in another. This is the
multi-job structure behind hardened macros: the child is implemented, packaged as
a library, and injected into the parent, which never sees its RTL.

.. graphviz:: _images/multi_job/hierarchical.dot
   :align: center

.. code-block:: python

   library = build_and()          # job 1: implement the child, package the views

   project = ASIC(Top())
   project.add_alias(And(), "rtl", None, None)   # blackbox the child's RTL
   project.add_asiclib(library)                  # inject its LEF/LIB
   project.run()                                 # job 2: implement the parent

:ref:`Instantiating a hardened module <hardened_modules>` works this through end
to end, and :ref:`Hardening parameterized modules <uniquify_modules>` automates
it across every parameterization of a module.

Putting It Together
===================

The three patterns compose into flows that no single flowgraph can express,
because the decisions between jobs are ordinary Python:

.. graphviz:: _images/multi_job/together.dot
   :align: center

Read it as an alternation. SiliconCompiler runs a job (grey); your script reads
the result and decides what to run next (yellow); repeat. A synthesis job fans
out into one implementation job per configuration, your code compares them, and
either proceeds to signoff or adjusts and re-runs.

The flowgraph handles what is static -- the steps inside a job, and the edges
between them. Your script handles what depends on a result, because that is not
something a static graph can express.

.. seealso::
   * :ref:`Parallel Job Execution <parallel_execution>` -- running the jobs above
     concurrently.
   * :ref:`Working with Metrics <dev_metrics>` -- what is available to compare.
   * :ref:`Directory structures <build_directory>` -- where each job's outputs
     land.
