.. _directory_structures:

####################
Directory Structures
####################

SiliconCompiler writes to two places: a **build directory** for the artifacts of
a compilation, and a **home directory** (``~/.sc``) for data and settings shared
across every project on the machine.

This page describes both, so you know where to look for a report, what is safe to
delete, and what to check into version control.

.. _build_directory:

The build directory
===================

Everything a run produces goes under the build directory, which defaults to
``build/`` relative to where you ran the script.
Below that, output is nested by :term:`design` name and then by
:term:`job` name, so several designs and several jobs can share one build
directory without colliding:

.. code-block:: text

   build/                              <- option,builddir  (default: "build")
   └── heartbeat/                      <- design name
       └── job0/                       <- option,jobname   (default: "job0")
           ├── heartbeat.pkg.json      <- the job manifest
           ├── job.log                 <- log for the most recent run
           ├── job.20260731-085354.log <- rotated logs from previous runs
           ├── sc_collected_files/     <- inputs copied in for reproducibility
           ├── elaborate/              <- one directory per step
           │   └── 0/                  <- one directory per index
           └── synthesis/
               └── 0/

The two paths worth remembering are the **job manifest**,
``build/<design>/<jobname>/<design>.pkg.json``, which is the complete
:term:`schema` as it stood at the end of the run, and **job.log**, which is the
full log of that run.
On each new run the previous ``job.log`` is renamed with the timestamp of its
last write rather than overwritten, and the five most recent are kept.

``sc_collected_files/`` holds copies of input files that were marked for
collection, so the job directory contains everything needed to rebuild even if
the original sources move. It only appears when a run actually collects files.

Inside a node directory
-----------------------

Each :term:`flowgraph node` -- one (:term:`step`, :term:`index`) pair -- runs in
its own directory and leaves its results there:

.. code-block:: text

   synthesis/0/
   ├── inputs/               <- files received from the preceding node(s)
   │   ├── heartbeat.v
   │   └── heartbeat.pkg.json
   ├── outputs/              <- files passed on to the following node(s)
   │   ├── heartbeat.vg
   │   └── heartbeat.pkg.json
   ├── reports/              <- structured tool reports the metrics are read from
   ├── synthesis.log         <- the tool's own output
   ├── synthesis.errors      <- lines from that log matched as errors
   ├── synthesis.warnings    <- lines from that log matched as warnings
   ├── sc_synthesis_0.log    <- SiliconCompiler's log for this node
   ├── sc_manifest.tcl       <- the manifest, exported for the tool to read
   └── replay.sh             <- re-runs this node on its own

Two details of this layout are worth knowing, because they explain most of what
you will do with a build directory:

**There are two logs, and they answer different questions.**
``<step>.log`` is what the tool printed -- the place to look when the tool itself
failed. ``sc_<step>_<index>.log`` is what SiliconCompiler did around it: which
files it resolved, which parameters it passed, how long the task took.
``<step>.errors`` and ``<step>.warnings`` are the lines of the tool log that
matched the task's error and warning patterns, which is also how the
``errors`` and ``warnings`` :term:`metrics <metric>` are counted.

**Every node carries its own manifest.**
``inputs/<design>.pkg.json`` is the schema as the node received it, and
``outputs/<design>.pkg.json`` is the schema as the node left it, with the
:term:`metrics <metric>` and :term:`records <record>` it produced.
This is what makes a single node reproducible: ``replay.sh`` re-runs it from its
own inputs, and :ref:`sc-issue <app-sc-issue>` packages it up as a standalone
test case::

    sc-issue -cfg build/<design>/<jobname>/<step>/<index>/inputs/<design>.pkg.json

.. note::
   The exported tool manifest is named ``sc_manifest.<suffix>``, where the
   suffix depends on what the tool reads -- ``.tcl`` for OpenROAD and Yosys,
   ``.json`` for Python-driven tools such as KLayout. Not every task exports
   one.

Controlling the build directory
-------------------------------

.. list-table::
   :header-rows: 1
   :widths: 28 22 50

   * - Parameter
     - Default
     - Effect
   * - :keypath:`option,builddir`
     - ``build``
     - Root of the build tree. Relative paths resolve against the directory the
       script was run from. Set it with ``project.option.set_builddir(path)``.
   * - :keypath:`option,jobname`
     - ``job0``
     - Names the job directory. Use it to keep runs side by side for comparison.
   * - :keypath:`option,clean`
     - ``False``
     - Runs from scratch. By default a re-run *resumes*: nodes that already
       completed are reused rather than re-executed. Setting ``clean`` discards
       that state and empties the job directory first, unless
       :keypath:`option,from` is set or ``jobincr`` moves the run elsewhere.
   * - :keypath:`option,jobincr`
     - ``False``
     - Only takes effect together with ``clean``. Instead of emptying the
       existing job directory, the run moves to the next unused job name
       (``job0`` becomes ``job1``), so the earlier job survives for comparison.
       On its own, ``jobincr`` does nothing.

The build directory is entirely derived output. It is safe to delete, and it
should not be checked into version control.

.. _sc_home:

The SiliconCompiler home directory
==================================

``~/.sc`` holds everything that is shared between projects rather than produced
by one:

.. code-block:: text

   ~/.sc/
   ├── cache/           <- downloaded data sources (PDKs, libraries, designs)
   ├── settings.json    <- your persistent defaults
   ├── credentials      <- remote server address and login
   └── tool_build/      <- scratch space for sc-install

On Windows the same directory is ``C:\Users\<username>\.sc\``.

The data cache
--------------

Any :term:`dataroot` that points at a git repository or a downloadable archive is
fetched once into ``~/.sc/cache`` and reused by every project afterwards. Entries
are named ``<name>-<reference>-<hash>``, where the reference is the requested
version and the hash distinguishes sources that resolve differently:

.. code-block:: text

   ~/.sc/cache/
   ├── lambdapdk-v0.2.17-49afb2b188ee16ae/
   ├── lambdapdk-v0.2.17-49afb2b188ee16ae.lock
   └── ...

The ``.lock`` files coordinate concurrent runs so that two processes do not
download the same package at once; they are not data and can be ignored.

Set :keypath:`option,cachedir` to move the cache -- to shared storage on a
cluster, for instance, so that every user and every compute node resolves
packages from one place:

.. code-block:: python

   project.option.set_cachedir("/shared/sc_cache")

The cache is safe to delete; anything missing is downloaded again on the next
run. Deleting it while a run is in progress is not.

Settings and credentials
------------------------

``settings.json`` holds defaults applied to every new :class:`.Project` -- your
preferred scheduler, log verbosity, and so on -- written by
:meth:`.OptionSchema.write_defaults`. An administrator can also supply
machine-wide defaults from outside your home directory, at
``/etc/siliconcompiler/settings.json`` on Linux and macOS or
``%PROGRAMDATA%\siliconcompiler\settings.json`` on Windows.
:ref:`User Settings <user_settings>` covers the file format and the precedence
rules between the two.

``credentials`` holds the address and login for a remote server, written by
``sc-remote -configure``. Note that it has no file extension, although its
contents are JSON. Point :keypath:`option,credentials` at a different file to
use more than one server. See :ref:`Remote Processing <remote_processing>`.

``tool_build/`` is where ``sc-install`` builds tools from source before
installing them, by default into ``~/.local``. It is scratch space and can be
deleted.

.. note::
   Except for ``tool_build/``, nothing in ``~/.sc`` is required: SiliconCompiler
   creates what it needs on demand. Deleting the whole directory costs you your
   saved defaults and credentials, and means every package is downloaded again.
