.. _debug_tutorial:

##################
When a Run Fails
##################

A failed build gives you a one-line error and a directory full of files. This
page is about turning that into a diagnosis.

The order below is deliberate: it is roughly the order in which failures happen,
and each stage is cheaper to check than the one after it.

First: which stage failed?
==========================

Read the last few lines of the terminal. SiliconCompiler distinguishes three
kinds of failure, and they need different responses:

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - What you see
     - What it means
   * - ``Cannot resolve path …``
     - **Before anything ran.** A file in the schema does not exist. Nothing was
       compiled; no tool was started.
   * - ``Run failed: Tools requirements not met``
     - **Before the tool ran.** The node was set up but a requirement was
       missing -- usually a file, sometimes a tool.
   * - ``Run failed`` after node output
     - **The tool ran and failed.** Its own log is where the answer is.

The first two are configuration problems in your script. The third is a design
or tool problem, and is the only one where you need the build directory.

Missing files
=============

By far the most common failure, and the one most often reported as a bug:

.. code-block:: text

   | ERROR | Cannot resolve path missing.v in required file keypath
   |         [library,nope,fileset,rtl,file,verilog] for lint/0.
   | ERROR | Run failed: Tools requirements not met

Read the keypath backwards: a **verilog** file, in the **rtl**
:term:`fileset`, of the library **nope**, was needed by node **lint/0** and could
not be found. The path is reported exactly as you wrote it, so if it looks
relative, it was resolved against a :term:`dataroot` that does not contain it.

Check the whole design before running, which is much faster than a failed run:

.. code-block:: python

   assert design.check_filepaths()

Most examples expose this as a target -- ``smake check``. See
:ref:`Add files to a fileset <howto>` for how paths and dataroots relate.

When the tool itself fails
==========================

Now the build directory matters. Every node has its own, and two logs that
answer different questions:

.. code-block:: text

   build/<design>/<jobname>/<step>/<index>/
   ├── inputs/                 <- what the node received
   ├── outputs/                <- what it produced
   ├── reports/                <- structured reports the metrics come from
   ├── <step>.log              <- what the TOOL printed
   └── sc_<step>_<index>.log   <- what SiliconCompiler did around it

``<step>.log`` is the tool's own output -- read it first when a tool failed.
``sc_<step>_<index>.log`` is SiliconCompiler's: which files it staged, the exact
command line it ran, what it read back out. Read that when the tool looks like it
was given the wrong thing.

``build/<design>/<jobname>/job.log`` is the whole run, and the error message
prints its path for you.

:ref:`Directory structures <build_directory>` documents the rest of the tree.

Reproducing it faster
=====================

A failing node can usually be re-run on its own, without repeating what already
worked. A re-run **resumes** by default:

.. code-block:: python

   project.option.add_from("synthesis")   # start here, reuse earlier results
   project.option.add_to("synthesis")     # and stop here

That reuses the inputs the failing node received last time, so the loop is edit,
re-run one node, look. See
:ref:`Run only part of the flow <howto>` for the details, including how to
drop individual nodes with :keypath:`option,prune`.

To start clean instead -- when you suspect stale state rather than a real
failure:

.. code-block:: python

   project.option.set_clean(True)      # do not resume; rebuild from scratch

Seeing more
===========

Two different knobs, often confused:

.. code-block:: python

   project.logger.setLevel("DEBUG")    # SiliconCompiler's own verbosity
   project.option.set_quiet(False)     # let the tool's output through

The first changes what SiliconCompiler tells you about scheduling, file staging
and metric collection. The second controls whether the tool's own chatter reaches
your terminal -- it is in ``<step>.log`` either way. If a run looks stuck,
``quiet=False`` is usually what you want.

Checking configuration without running
======================================

.. code-block:: python

   project.check_manifest()

.. warning::
   Run this **after** :meth:`.Project.run()`. Library dependency resolution
   happens inside ``run()``, so a call before it reports errors about a
   configuration that is actually correct -- it is not a usable pre-flight
   check. To validate a configuration before building, use
   ``design.check_filepaths()`` above.

Asking for help
===============

When the failure is in a tool rather than your script, ``sc-issue`` packages a
self-contained, runnable reproduction -- the manifest, the input files and the
tool setup for one node:

.. code-block:: bash

   sc-issue -cfg build/<design>/<jobname>/<step>/<index>/inputs/<design>.pkg.json

It writes ``sc_issue_<...>.tar.gz``, which anyone can replay with:

.. code-block:: bash

   sc-issue -run sc_issue_<...>.tar.gz

By default it includes the libraries the node used. ``-exclude_libraries`` with
``-add_library <name>`` narrows that, which matters if some of them are
confidential. See :ref:`sc-issue <app-sc-issue>` for the full switch list.

Attach that archive to a `Discussion
<https://github.com/siliconcompiler/siliconcompiler/discussions>`_ or an
`issue <https://github.com/siliconcompiler/siliconcompiler/issues>`_. A
reproduction turns "it failed" into something someone can fix.

Failures that are not errors
============================

A run can succeed and still be wrong. The summary table is where that shows up:

* :keypath:`metric,errors` and :keypath:`metric,warnings` -- non-zero on a
  "successful" run is worth reading.
* :keypath:`ASIC,metric,setupslack` / :keypath:`ASIC,metric,holdslack` -- negative means
  timing did not close, and no tool will stop you.
* :keypath:`ASIC,metric,drvs` -- routing and connectivity violations.
  :keypath:`ASIC,metric,drcs` is the different, geometric one; see
  :ref:`the FAQ <faq>`.
* :keypath:`ASIC,metric,unconstrained` -- endpoints with no timing constraint. A
  large number usually means a missing or wrong :term:`SDC`.

:ref:`Checklists <checklists>` exist to turn those into a pass/fail gate rather
than something you have to remember to look at.

.. seealso::
   :ref:`Working with Metrics <dev_metrics>` for reading any of these back out
   of a run, and :ref:`How do I…? <howto>` for the recipes referenced above.
