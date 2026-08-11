.. _migration_guide:

.. index:: ! Chip, ! migration, ! porting an old script, ! legacy API

###################################
Migrating from the ``Chip`` API
###################################

If you have a script that starts like this, you are using an API that no longer
exists:

.. code-block:: python

   from siliconcompiler import Chip

   chip = Chip('heartbeat')
   chip.input('heartbeat.v')
   chip.load_target('freepdk45_demo')
   chip.run()

The ``Chip`` class was removed in **v0.35.0** (August 2025) and replaced by a
:class:`.Design` object plus a project object. This page maps the
old names onto the new ones.

.. note::
   This page is kept indefinitely, and deliberately spells out the old names in
   full. Years of tutorials, papers, forum answers and blog posts use the
   ``Chip`` API, search engines still surface documentation for releases that
   predate the change, and code assistants trained on all of it will happily
   write ``Chip('mydesign')`` today. If you arrived here from one of those, you
   are in the right place.

   Parameter-level changes -- keys added, renamed or removed inside the schema
   itself -- are recorded separately in :ref:`Schema Changes <schema_changelog>`.

Why it changed
==============

``Chip`` was one object holding two unrelated things: *what* you are building
and *how* this particular build is configured. That made a design impossible to
reuse -- to build the same RTL for two processes, or reuse a block inside a
larger chip, you rebuilt the object from scratch.

The replacement separates them:

* A :class:`.Design` describes source code: files, grouped into
  :term:`filesets <fileset>`, with a top module and include paths. It says
  nothing about a process or a flow, so the same ``Design`` can be built many
  ways, and one design can depend on another.
* A **project** describes one compilation of a design. Use the class that
  matches the job -- :class:`.ASIC`, :class:`.FPGA`, :class:`.Lint` or
  :class:`.Sim` -- which is what replaces the old ``option,mode`` flag. Each one
  brings the schema, constraints and metrics for its domain, so an ``ASIC``
  carries the ``asic,*`` parameters that a ``Lint`` has no use for.
  :class:`.Project` is the base class they extend, and is not the one to write a
  build script against: it has no domain section, so an ASIC target applied to a
  bare ``Project`` fails with ``AttributeError``.

The second change is that configuration moved from string keypaths to **typed
accessors** -- ``project.option.set_remote(True)`` rather than
``chip.set('option', 'remote', True)``. Keypaths still work and are still the
layer underneath; see :ref:`Working with the Schema <schema_access>` for when to
use which.

The same script, before and after
=================================

The old form, from the ``heartbeat`` example as it shipped in v0.34.3:

.. code-block:: python

   from siliconcompiler import Chip
   from siliconcompiler.targets import freepdk45_demo

   chip = Chip('heartbeat')
   chip.register_source("heartbeat-example", __file__)
   chip.input("heartbeat.v", package="heartbeat-example")
   chip.input("heartbeat.sdc", package="heartbeat-example")
   chip.use(freepdk45_demo)
   chip.run()
   chip.summary()
   chip.show()

The same build today. It is pulled in from ``examples/heartbeat/heartbeat.py``,
so it is exercised by the test suite rather than transcribed here:

.. literalinclude:: tutorials/examples/heartbeat/heartbeat.py
   :language: python
   :start-at: design = Design
   :end-at: project.show()
   :dedent: 4

Four differences to notice, because they account for most of the porting work:

#. **Two objects instead of one.** ``Design`` for the sources, ``ASIC`` for the
   build.
#. **Files carry a fileset.** ``input()`` guessed a file's role from its
   extension; ``add_file()`` requires you to name it, and the project then
   selects which filesets to compile with ``add_fileset()``.
#. **The top module is explicit.** It used to be inferred from the ``Chip`` name.
#. **A target is called, not "used".** ``skywater130_demo(project)`` instead of
   ``chip.use(...)`` or ``chip.load_target(...)``.

Objects and imports
===================

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Removed
     - Use instead
   * - ``Chip``
     - :class:`.Design` for the sources, plus one of
       :class:`.ASIC` / :class:`.FPGA` / :class:`.Lint` / :class:`.Sim` for the
       build (:class:`.Project` is their base class, not a substitute for them)
   * - ``ASICProject``
     - :class:`.ASIC`
   * - ``Library``, ``LibrarySchema``
     - :class:`.Design`. Since schema 0.54.0 a library *is* a
       design; :class:`.StdCellLibrary` adds the standard-cell
       specifics
   * - ``Flow``, ``FlowgraphSchema``
     - :class:`.Flowgraph`
   * - ``Schema`` (top-level export)
     - Nothing to import. A project *is* a schema -- ``get``, ``set``,
       ``getkeys`` and ``write_manifest`` are methods on it
   * - ``DesignSchema``, ``PDKSchema``, ``ASICSchema``, ``MetricSchema``, …
     - The ``…Schema`` suffix is gone from the public names:
       :class:`.Design`, :class:`.PDK`,
       :class:`.Checklist`, :class:`.Task`
   * - ``SiliconCompilerError``
     - Standard Python exceptions

.. warning::
   ``FPGA`` still exists and **means something different**. It used to be the
   FPGA *device* class; it is now the FPGA *project* class. The device is
   :class:`.FPGADevice`. Old code reading
   ``FPGA('mydevice')`` needs ``FPGADevice('mydevice')``.

Setting up a design
===================

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Old
     - New
   * - ``Chip('mydesign')``
     - ``Design('mydesign')``
   * - ``chip.set('design', 'top')``
     - ``design.set_topmodule('top', fileset='rtl')``
   * - ``chip.top()``
     - ``design.get_topmodule(fileset='rtl')``
   * - ``chip.input('f.v')``
     - ``design.add_file('f.v', fileset='rtl')`` -- the fileset is explicit
       rather than guessed from the extension
   * - ``chip.output(...)``
     - Outputs are produced by tasks, not declared on the design
   * - ``chip.register_source('name', __file__)``
     - ``design.set_dataroot('name', __file__)``
   * - ``package='name'`` keyword
     - ``dataroot='name'``. The schema field was renamed in schema 0.52.0, along
       with the ``find_files`` and ``check_filepaths`` arguments
   * - ``chip.add('option', 'idir', 'include')``
     - ``design.add_idir('include', fileset='rtl')``
   * - ``chip.add('option', 'define', 'SYNTHESIS')``
     - ``design.add_define('SYNTHESIS', fileset='rtl')``
   * - ``chip.import_flist('files.f')``
     - ``design.read_fileset('files.f', fileset='rtl')``
   * - ``chip.clock('clk', period=1.0)``
     - Removed with no direct equivalent -- the ``datasheet`` pin timing
       parameters it wrote are gone. Define clocks in an SDC file and add it to
       an ``sdc`` fileset
   * - ``chip.use(mylib)`` for a library
     - ``project.add_dep(mylib)``, or list its filesets through
       ``design.add_depfileset()``
   * - ``chip.swap_library(old, new)``
     - ``project.add_alias(old_dep, old_fileset, new_dep, new_fileset)``

Configuring and running
=======================

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Old
     - New
   * - ``chip.use(freepdk45_demo)``
     - ``freepdk45_demo(project)`` -- targets are still plain functions, and are
       called with the project
   * - ``chip.load_target('freepdk45_demo')``
     - Import the target and call it. The string form, and the ``option,target``
       parameter behind it, are both gone
   * - ``chip.set('option', 'mode', 'asic')``
     - Use the :class:`.ASIC` project class. ``option,mode`` was
       removed in schema 0.42.7
   * - ``chip.set('option', 'remote', True)``
     - ``project.option.set_remote(True)``
   * - ``chip.set('option', 'builddir', 'out')``
     - ``project.option.set_builddir('out')``
   * - ``chip.set('option', 'jobname', 'run1')``
     - ``project.option.set_jobname('run1')``
   * - ``chip.set('option', 'quiet', True)``
     - ``project.option.set_quiet(True)``
   * - ``chip.set('option', 'to', 'syn')``
     - ``project.option.add_to('syn')``; likewise ``add_from`` and ``add_prune``
   * - ``chip.set('option', 'flow', 'asicflow')``
     - ``project.set_flow(ASICFlow())``, or let the target set it
   * - ``chip.run()``, ``chip.summary()``, ``chip.show()``
     - Unchanged -- same names on the project
   * - ``chip.check_manifest()``
     - ``project.check_manifest()``, but call it **after** ``run()``: library
       dependencies are resolved during the run, so a pre-run call reports
       failures on a correct configuration
   * - ``chip.dashboard()``
     - The CLI dashboard now runs during ``run()`` automatically; disable it with
       ``project.option.set_nodashboard(True)``. For the web dashboard, use the
       ``sc-dashboard`` command
   * - ``chip.check_checklist()``
     - ``Checklist.check()`` -- see :ref:`Checklists and signoff <checklists>`
   * - ``chip.create_cmdline()``
     - Unchanged in name, now provided by ``CommandLineSchema`` on the project
   * - ``chip.error('message')``
     - Raise an exception, or log through ``project.logger``

Reading results and paths
=========================

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Old
     - New
   * - ``chip.get('metric', 'cellarea', step=…, index=…)``
     - Unchanged, but read it from the object ``run()`` returns: job metrics are
       reset on the live project when a run completes
   * - ``chip.getworkdir()``
     - ``siliconcompiler.utils.paths.workdir(project, step=…, index=…)``
   * - ``chip.getbuilddir()``
     - ``siliconcompiler.utils.paths.builddir(project)``
   * - ``chip.collect()``, ``chip.archive()``
     - ``siliconcompiler.utils.curation.collect(project)`` and
       ``archive(project)``
   * - ``chip.find_result(...)``, ``chip.snapshot()``
     - Unchanged -- same names on the project
   * - ``chip.find_node_file(...)``
     - ``project.find_result(...)``
   * - ``chip.hash_files(...)``, ``chip.check_filepaths()``
     - Unchanged in name, now schema methods; ``hash_files`` takes ``dataroot``
       where it took ``package``
   * - ``chip.help('option', 'remote')``
     - Removed. Parameter help text is in the
       :ref:`Schema Reference <schema>`, or ``project.getdict()``
   * - ``<design>.cfg``
     - ``<design>.pkg.json``. Manifests have been JSON with a ``.pkg.json``
       extension since well before the ``Chip`` removal; a ``.cfg`` path in a
       script or a ``sc-dashboard -cfg`` invocation is stale

Building flows, tools and libraries
===================================

Module-style setup functions became classes. Old flows, tool tasks, PDKs and
libraries were modules exposing a ``setup(chip)`` function plus a ``make_docs``
hook, discovered by import:

.. code-block:: python

   # old: siliconcompiler/flows/myflow.py
   def make_docs(chip):
       return setup()

   def setup(flowname='myflow'):
       flow = siliconcompiler.Flow(flowname)
       flow.node(flowname, 'import', parse)
       flow.node(flowname, 'syn', syn_asic)
       flow.edge(flowname, 'import', 'syn')
       return flow

Now each is a class, and ``make_docs`` is gone -- the documentation is generated
from the class and its docstring:

.. code-block:: python

   # new
   from siliconcompiler import Flowgraph

   class MyFlow(Flowgraph):
       '''One-line summary, which becomes the description in the docs.'''
       def __init__(self):
           super().__init__("myflow")
           self.node("elaborate", Elaborate())
           self.node("synthesis", ASICSynthesis())
           self.edge("elaborate", "synthesis")

The same shape applies elsewhere: a tool task subclasses
:class:`.Task` instead of exposing ``setup(chip)``,
``pre_process(chip)`` and ``post_process(chip)`` module functions; a standard
cell library subclasses :class:`.StdCellLibrary`; a PDK
subclasses :class:`.PDK`. Nodes take a task *instance* rather
than a module reference, and ``node()``/``edge()`` are methods on the flowgraph
rather than on the chip.

Targets are the exception: they are still functions taking a project, because a
target's job is to configure one.

See the :ref:`Advanced Guide <advanced_guide>` for how to write each of these, and
:ref:`Where your module belongs <module_placement>` before you decide which
repository it goes in -- that answer also changed.

The command line
================

There is **no** ``sc`` command, and there never was one after v0.35.0. The
entry points are ``sc-dashboard``, ``sc-issue``, ``sc-remote``, ``sc-server``,
``sc-show``, ``sc-install`` and ``smake``.

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Old
     - New
   * - ``sc heartbeat.v -target freepdk45_demo``
     - Write a Python script -- see the example above -- or use ``smake`` with a
       ``make.py``
   * - ``sc -target asic_demo``
     - ``python3 -m siliconcompiler.demos.asic_demo``
   * - ``sc -target asic_demo -remote``
     - ``python3 -m siliconcompiler.demos.asic_demo -remote``

Everything else -- ``sc-show``, ``sc-issue``, ``sc-remote`` and the rest --
kept its name and its arguments.

Still stuck?
============

If a symbol is not listed here, two places are worth checking before asking:
:ref:`Schema Changes <schema_changelog>` for anything that looks like a schema
key, and the :ref:`Python API <schema_api>` for a method name. Failing that, ask
in `Discussions
<https://github.com/siliconcompiler/siliconcompiler/discussions>`_ -- and please
say which version the old script targeted, because it tells us which era of the
API to translate from.
