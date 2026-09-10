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
   ├── cache/           <- everything kept between runs (see below)
   ├── settings.json    <- your persistent defaults
   ├── credentials      <- remote server address and login
   └── tool_build/      <- scratch space for sc-install

On Windows the same directory is ``C:\Users\<username>\.sc\``.

The cache
---------

``~/.sc/cache`` holds everything SiliconCompiler keeps between runs, in one
subdirectory per kind:

.. code-block:: text

   ~/.sc/cache/
   ├── dataroot/        <- downloaded data sources (PDKs, libraries, designs)
   └── tools/           <- caches the tools keep for themselves

Cached data goes in those subdirectories, never in the directory itself, which
holds nothing but the sweep's own ``.sc_cleanup`` timestamp.
:keypath:`option,cachedir` moves both areas together -- to shared storage on a
cluster, for instance, so that every user and every compute node resolves
packages from one place:

.. code-block:: python

   project.option.set_cachedir("/shared/sc_cache")

Both areas are safe to delete; anything missing is downloaded or rebuilt on the
next run. Deleting either while a run is in progress is not.

Data sources
^^^^^^^^^^^^

Any :term:`dataroot` that points at a git repository or a downloadable archive is
fetched once into ``dataroot/`` and reused by every project afterwards. Entries
are named ``<name>-<reference>-<hash>``, where the reference is the requested
version and the hash distinguishes sources that resolve differently:

.. code-block:: text

   ~/.sc/cache/dataroot/
   ├── lambdapdk-v0.2.17-49afb2b188ee16ae/
   ├── lambdapdk-v0.2.17-49afb2b188ee16ae.lock
   └── ...

The ``.lock`` files coordinate concurrent runs so that two processes do not
download the same package at once; they are not data and can be ignored. Their
modification time doubles as the entry's last-use time, stamped by every resolve.

Because nothing in a normal run removes the version an older project needed, this
area only grows. Every run therefore starts with a sweep of it: entries that
have not been resolved in 90 days are deleted, as is any ``.lock`` or
``.sc_lock`` file whose entry is already gone, whatever its age -- except one
taken in the last hour, which is kept in case a resolve is holding it and has yet
to create its directory. The sweep runs at most once a week per cache directory,
records when it last ran in ``.sc_cleanup``, and never interrupts a run. Both the age and the
interval are configurable, and the sweep can be switched off entirely -- see
:ref:`User Settings <user_settings>`. To collect the cache on demand instead,
with a threshold of your own:

.. code-block:: bash

   python3 -m siliconcompiler.apps.utils.cleanup -days 30 -dryrun

Upgrading from a release before the cache was split, the old entries sit loose in
``~/.sc/cache`` rather than in ``dataroot/``. Nothing moves them: they are swept
on the same 90-day clock as everything else, and anything still wanted is
downloaded again into the new layout the next time it resolves. A cache shared
with a machine still on an older release therefore loses the entries that release
is using, and that release downloads them again -- the same one-time cost, paid
on the other machine.

Tool caches
^^^^^^^^^^^

``tools/<tool>/`` is where a tool keeps whatever it carries from one run to the
next. Unlike a node's working directory, which is emptied at the start of every
run, this survives, and it is shared across every design built with that tool.

A tool that keeps a cache reads the directory from an environment variable, and
defaults it to somewhere under ``~/.cache``. That is outside
:keypath:`option,cachedir`, so nothing SiliconCompiler manages sees it, and it is
absent from a task container, so a containerised run starts cold every time. The
drivers of such tools point that variable at ``tools/<tool>`` instead. Verilator
is the clearest case -- its generated makefile invokes ccache on every C++ build,
so ``CCACHE_DIR`` lands here -- and each tool gets its own subdirectory rather
than sharing one, because two tools rarely compile the same thing with the same
flags. Set the variable yourself, in the environment or on the task, and your
setting is left alone.

Sharing across designs is what a compiler cache wants, but not every cache can:
a cache whose contents are only valid for one task configuration has to be kept
apart from the others. A driver in that position names a subdirectory after the
task's :ref:`digest <task_digest>` instead of sharing ``tools/<tool>/``
directly.

Nothing collects this area. A tool that keeps a cache is expected to cap it
itself -- ccache does, at 5GB by default -- so if you want it gone, delete it.

.. _task_digest:

Naming things after a task
^^^^^^^^^^^^^^^^^^^^^^^^^^

:meth:`.Task.get_digest` returns a hex digest of everything that configures a
task -- its command line, threads, scripts, environment, tool version
requirement, and every keypath its driver declared with
:meth:`.Task.add_required_key`. Two tasks configured the same way get the same
digest; two that differ anywhere, including in a single boolean, do not:

.. code-block:: python

   class MyTask(Task):
       @property
       def cachedir(self):
           return os.path.join(super().cachedir, self.get_digest(length=16))

The digest is computed from the configuration as written. It reads no files,
resolves no :term:`dataroot`, runs no executable and does not depend on
:keypath:`option,hash`, so it costs nothing and comes out the same on every
machine -- a cache directory named after it can be shared across a cluster. What
that leaves out is worth knowing before you rely on it: the contents of the input
files, and the version of the tool actually installed. A driver that needs either
composes it -- :meth:`.Task.get_exe_version` for the second -- or requires the
keys that stand in for them, such as a dataroot's ``tag``.

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
