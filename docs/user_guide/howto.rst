.. _howto:

.. index:: ! how do I, ! recipes, ! cookbook

##########
How do I…?
##########

A task-oriented reference: the shortest correct way to do common things.
Feel free to suggest new entries.

For questions rather than method calls -- what a target is, whether the public
server is confidential, why a run failed -- see the
:ref:`Frequently Asked Questions <faq>`.

Entries are grouped by what you are trying to do, roughly in the order people
need them.

Set up a build
==============

Create a design object
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from siliconcompiler import Design
   design = Design('<design>')

Dataroot: register a new source of files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   design.set_dataroot("<name>", "<path>", tag="<version>")

The path may be a local directory, a git URL, or an archive URL. ``tag`` applies
to remote sources only, and is a git commit, branch, or tag. See
:term:`dataroot`.

Dataroot relative to my current file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   design.set_dataroot('<name>', __file__)

Create an ASIC project object
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from siliconcompiler import ASIC
   project = ASIC(design)

Add files to a fileset
^^^^^^^^^^^^^^^^^^^^^^

.. index:: ! add_file, ! source files, ! add sources, ! filetype

Group a design's files into named :term:`filesets <fileset>` and register them
against a :term:`dataroot` so the paths survive being run from elsewhere. The
:term:`fileset` and filetype are inferred from the extension:

.. code-block:: python

   design.set_dataroot("mydesign", __file__)

   with design.active_dataroot("mydesign"), design.active_fileset("rtl"):
       design.set_topmodule("mydesign")
       design.add_file("rtl/mydesign.v")        # -> fileset "rtl", type verilog

   with design.active_dataroot("mydesign"), design.active_fileset("sdc"):
       design.add_file("constraints/mydesign.sdc")

   with design.active_dataroot("mydesign"), design.active_fileset("testbench"):
       design.add_file("tb/mydesign_tb.sv")

Pass ``filetype=`` explicitly when the extension does not imply it. A design may
carry as many filesets as you like -- only the ones you activate are compiled.

Activate filesets
^^^^^^^^^^^^^^^^^

.. index:: ! active fileset, ! select fileset, ! which files are compiled

Choose which of the design's filesets this run compiles:

.. code-block:: python

   project.add_fileset(["rtl", "sdc"])     # ignores "testbench"

This is how one design serves several flows: an ASIC build activates ``rtl`` and
``sdc``, while a simulation activates ``rtl`` and ``testbench``.

Run a compilation
^^^^^^^^^^^^^^^^^

.. code-block:: python

   project.run()

See what happened
=================

Display my layout
^^^^^^^^^^^^^^^^^

.. code-block:: python

    project.show()

Display a previous run from the command line
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. index:: ! sc-show, ! viewer

.. code-block:: bash

   sc-show -design <name>

Change the logging level, or quieten the output
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. index:: ! logging, ! log level, ! logger, ! verbose, ! verbosity, ! debug output, ! quiet, ! silence

Two different things control how much you see.

SiliconCompiler's own messages come from a standard Python logger, so set its
level directly. There is no ``option`` for this:

.. code-block:: python

    project.logger.setLevel("DEBUG")     # or "INFO" (the default), "WARNING", "ERROR"

Tool output is separate. It is summarised by default; set
:keypath:`option,quiet` to suppress it entirely, or unset it to see everything
the tool prints:

.. code-block:: python

    project.option.set_quiet(True)                              # whole run
    project.option.set_quiet(True, step="synthesis", index="0")  # one node

Either way the full tool log is always written to
``<step>.log`` in the node directory -- see
:ref:`Directory structures <directory_structures>`.

Use the manifest from a previous run
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. index:: ! pkg.json, ! resume

.. code-block:: python

    from siliconcompiler import Project

    project = Project.from_manifest("build/<design>/<jobname>/<design>.pkg.json")

Control a run
=============

Run only part of the flow
^^^^^^^^^^^^^^^^^^^^^^^^^

.. index:: ! from, ! to, ! prune, ! partial run, ! rerun a step, ! only synthesis, ! resume

A re-run resumes by default: nodes that already completed are reused, so
restarting from a step re-runs it and everything downstream.

.. code-block:: python

   project.option.add_from("synthesis")    # start here, reusing earlier results
   project.option.add_to("synthesis")      # and stop here

:keypath:`option,from` and :keypath:`option,to` take **step names only**, not
indices -- a deliberate choice to keep them simple. To drop individual
(step, index) nodes, use :keypath:`option,prune`:

.. code-block:: python

   project.option.add_prune(("floorplan.init", "0"))

Start a fresh run
^^^^^^^^^^^^^^^^^

.. code-block:: python

   project.option.set_clean(True)

Start a fresh run and keep the old one
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. index:: ! jobname, ! jobincr, ! job increment

.. code-block:: python

   project.option.set_clean(True)
   project.option.set_jobincr(True)

Start a fresh run using the previous run information
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   project.option.set_clean(True)
   project.option.set_jobincr(True)
   project.option.add_from('floorplan')

Control how much of the machine a run uses
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. index:: ! threads, ! cores, ! parallelism, ! maxnodes, ! maxthreads, ! CPU usage, ! concurrency

Two job-wide limits, both defaulting to the number of available CPU cores:

.. code-block:: python

   project.option.scheduler.set_maxnodes(4)     # concurrent nodes in the job
   project.option.scheduler.set_maxthreads(8)   # threads available to each task

:keypath:`option,scheduler,maxnodes` bounds how many
:term:`flowgraph nodes <flowgraph node>` run at once;
:keypath:`option,scheduler,maxthreads` bounds each task's own threading. On a
machine you are still using for other work, lowering both is usually what you
want -- otherwise a wide flow will happily take every core.

To override the thread count for one task rather than the whole job:

.. code-block:: python

   from siliconcompiler.tools.yosys.syn_asic import ASICSynthesis

   ASICSynthesis.find_task(project).set_threads(4, step="synthesis", index="0")

Build directory
^^^^^^^^^^^^^^^

.. index:: ! builddir, ! build tree, ! output directory

.. code-block:: python

    project.option.set_builddir("/path/to/build")

See :ref:`Directory structures <build_directory>` for what a run writes there.

Cache directory
^^^^^^^^^^^^^^^

.. index:: ! cachedir, ! package cache, ! download cache

.. code-block:: python

    project.option.set_cachedir("/path/to/cache")

Defaults to ``~/.sc/cache``; see :ref:`the SC home directory <sc_home>`.

Preserve options across sessions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Options such as scheduler information can be preserved :ref:`across sessions
<user_settings>`:

.. code-block:: python

   project.option.write_defaults()

Check my setup before running
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. index:: ! check_manifest, ! validate, ! preflight

.. code-block:: python

    project.check_manifest()

Extend SiliconCompiler
======================

Set up a new tool
^^^^^^^^^^^^^^^^^

See :ref:`Tools <dev_tools>`

Set up a new flow
^^^^^^^^^^^^^^^^^

See :ref:`Flows <dev_flows>`

Set up a new PDK
^^^^^^^^^^^^^^^^

See :ref:`PDKs <dev_pdks>`

Set up a new library
^^^^^^^^^^^^^^^^^^^^

See :ref:`Libraries <dev_libraries>`

Set up a new target
^^^^^^^^^^^^^^^^^^^

See :ref:`Targets <dev_targets>`

Reuse a block as a hardened macro
=================================

Use a macro I already have
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. index:: ! hard macro, ! use a macro, ! instantiate a macro, ! LEF, ! blackbox, ! add_asiclib, ! add_alias, ! macro placement

.. warning::
   Adding a ``.lef`` to your design's own fileset does **not** work::

       design.add_file("mymacro.lef", fileset="rtl")   # wrong

   The parent will synthesize the macro's RTL anyway, and place-and-route then
   fails with ``LEF master ... not found``. A macro is a *library*, not a source
   file.

Package the views into a :class:`.StdCellLibrary`:

.. code-block:: python

   from siliconcompiler import StdCellLibrary

   macro = StdCellLibrary("mymacro")
   macro.set_dataroot("macro", __file__)
   macro.add_asic_pdk("skywater130")            # must match the parent's PDK

   with macro.active_dataroot("macro"), macro.active_fileset("models.physical"):
       macro.add_file("mymacro.lef")            # abstract view for place & route
       macro.add_file("mymacro.gds")            # layout, merged into the final GDS
       macro.add_asic_aprfileset()

   with macro.active_dataroot("macro"), macro.active_fileset("models.timing.typical"):
       macro.add_file("mymacro_typical.lib")    # timing view
       macro.add_asic_libcornerfileset("typical", "nldm")

Then, in the parent project, do two things -- **both are required**:

.. code-block:: python

   project.add_alias(mymacro_design, "rtl", None, None)   # 1. blackbox the RTL
   project.add_asiclib(macro)                             # 2. inject the views

   # Macros need room. Too small a die and the placer cannot fit them.
   project.constraint.area.set_diearea_rectangle(250, 250, coremargin=10)

Without the alias the parent re-synthesizes the block instead of instantiating
the hardened version; without the library the tools have no physical or timing
view of it.

:ref:`Instantiating a hardened module <hardened_modules>` works through this
end to end, including producing the macro from a first build.

Harden a parameterized module so I can reuse it as a macro
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A hardened macro has no parameters, so a parameterized module cannot be
hardened directly. Use :class:`.Uniquified`, which generates a parameter-free
variant per used parameter combination plus a wrapper that dispatches to
them. See the :ref:`uniquify tutorial <uniquify_modules>` and the
:ref:`Uniquify API <uniquify_api>`.

.. code-block:: python

   from siliconcompiler import ASIC
   from siliconcompiler.targets import freepdk45_demo
   from siliconcompiler.tools.slang.utils.macro import Uniquified

   # parent_design: your Design that instantiates the parameterized module.
   uq = Uniquified(parent_design, ["mymodule"])
   uq.build(target=freepdk45_demo)   # harden every used parameterization

   project = ASIC(parent_design)
   project.add_fileset("rtl")
   freepdk45_demo(project)
   uq.wireup(project)                # alias wrappers + inject macros

Find out which parameter values my module is instantiated with
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Construct :class:`.Uniquified` (construction only elaborates and generates in
memory -- no disk writes, no tools) and read its state:

.. code-block:: python

   uq = Uniquified(parent_design, ["mymodule"])
   print(uq.variants)   # {'mymodule': ['mymodule__N8', 'mymodule__N16']}

Rebuild only some hardened variants
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Pass ``macros`` to :meth:`.Uniquified.build` as a variant name, a module
name, or a glob; add ``rebuild=True`` to force a rebuild even if a cached
macro exists.

.. code-block:: python

   uq.build(target=freepdk45_demo, macros="mymodule__N8", rebuild=True)

Schema internals
================

Avoid rebuilding an expensive object (such as a PDK) many times
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If a schema object is a pure function of its construction arguments, base it
on ``CachedSchema``. Instances are built once per unique (hashable) set of
arguments, and the shared, frozen instance is returned on subsequent
constructions. This is useful for heavy objects, like PDKs, that would
otherwise be re-created dozens of times while loading a target.

.. code-block:: python

   from siliconcompiler import PDK
   from siliconcompiler.schema import CachedSchema

   class MyPDK(PDK, CachedSchema):
       def __init__(self):
           super().__init__("mypdk")
           # ... expensive schema population ...

   MyPDK() is MyPDK()   # True -- same shared instance, built only once

The shared instance is *frozen*: calling ``set``, ``add``, ``unset``,
``remove``, or using ``EditableSchema`` on it raises a
``SchemaFrozenError``. This protects the shared object from accidental
modification.

Get a modifiable version of a frozen (cached) object
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use ``copy()``. A copy is always mutable and fully independent of the shared
instance, so you are free to modify it. Objects reloaded from a manifest
(for example, inside a run) are likewise mutable.

.. code-block:: python

   my_pdk = MyPDK()          # frozen, shared
   local = my_pdk.copy()     # mutable, independent
   local.set("pdk", "foundry", "virtual")

To modify a frozen object in place (for example, to write resolved file
paths or hashes back into a shared object during a run), use the ``_thaw``
context manager, which restores the frozen state on exit:

.. code-block:: python

   with my_pdk._thaw():
       my_pdk.set(*keypath, hashes, field="filehash")

.. warning::
   ``_thaw()`` is internal API -- the leading underscore is not decorative. It
   exists for SiliconCompiler's own run machinery, carries no compatibility
   guarantee, and mutating a shared instance affects every holder of it.
   ``copy()`` is the supported answer; reach for ``_thaw()`` only when you
   genuinely need the mutation to be visible through the shared object.
