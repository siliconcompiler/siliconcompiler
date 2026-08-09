.. _picorv32_example:

#####################
Building Your Own SoC
#####################

This tutorial builds an ASIC containing a PicoRV32 RISC-V CPU core, and then the
same core wired to an SRAM -- the first step toward a real system-on-chip.

.. image:: /_screenshots/picorv32_ram_layout.png
   :align: center

It is the natural next step after the :ref:`Quickstart <quickstart_guide>`,
because it introduces the two things that quickstart's single-file design does
not: **sources fetched from another repository**, and **composing your design out
of someone else's**.

Everything here comes from
`examples/picorv32 <https://github.com/siliconcompiler/siliconcompiler/tree/main/examples/picorv32>`__,
which is three files:

.. code-block:: text

   examples/picorv32/
   ├── make.py            <- the build script; everything below is in here
   ├── picorv32.sdc       <- clock constraint
   └── picorv32_top.v     <- wrapper that connects the core to an SRAM

The CPU source is **not** among them, and does not need to be downloaded --
see below.

Running It
==========

From that directory:

.. code-block:: bash

   smake syn                              # synthesis only, quickest check
   smake asic                             # full RTL-to-GDS, bare core
   smake asic --fileset rtl.memory        # full RTL-to-GDS, core + SRAM

``make.py`` exposes each function as a target;
:ref:`smake <app-smake>` discovers them and turns their arguments into
command-line switches. ``smake --help`` lists what is available.

The default PDK is ``freepdk45``; ``asap7`` and ``gf180`` also work
(``--pdk asap7``), because the design carries a matching constraint fileset for
each. The full flow takes appreciably longer than the Quickstart's heartbeat --
most of it in routing.

Where the Sources Come From
===========================

The design does not vendor the CPU. It declares a :term:`dataroot` pointing at
the upstream repository, pinned to a commit, and SiliconCompiler fetches and
caches it on first use:

.. literalinclude:: examples/picorv32/make.py
   :language: python
   :start-after: # Define data sources using 'dataroots'.
   :end-before: # A 'fileset' is a collection of files
   :dedent: 8

This is the pattern to copy for any third-party RTL. Pinning the commit is what
makes the build reproducible; without it, "the same script" silently means
something different next month. The cache lives in
:ref:`~/.sc/cache <sc_home>`, so the fetch happens once per machine, not once
per run.

Part 1: The Bare Core
=====================

The ``rtl`` :term:`fileset` is the core on its own:

.. literalinclude:: examples/picorv32/make.py
   :language: python
   :start-after: # This block defines the base RTL fileset.
   :end-before: # This block defines a more complex RTL configuration
   :dedent: 8

Building it is the same three steps as any other project -- load the design, add
the filesets, apply a target:

.. literalinclude:: examples/picorv32/make.py
   :language: python
   :pyobject: asic

.. image:: /_screenshots/picorv32_layout.png
   :align: center

I/O signals are placed around the edges of the die area without a pin
constraint, which is why they appear evenly distributed rather than grouped.

Part 2: Adding an SRAM
======================

A CPU core is not much use without memory. A real SoC would also want a SPI
interface for external non-volatile memory, a UART, a debug interface and a
cache -- this adds the first of those pieces.

The SRAM does not have to be built or downloaded. ``lambdalib`` ships a
single-port RAM, and the ``rtl.memory`` fileset composes it with the core:

.. literalinclude:: examples/picorv32/make.py
   :language: python
   :start-after: # This block defines a more complex RTL configuration
   :end-before: # Define Synopsys Design Constraints (SDC)
   :dedent: 8

Two things are worth pulling out of that block, because together they are the
whole mechanism for building a design out of other designs:

* :meth:`.Design.add_depfileset` **declares a dependency on another design's
  fileset.** ``add_depfileset(self, "rtl")`` pulls in this design's own bare-core
  fileset, and ``add_depfileset(Spram(), "rtl")`` pulls in the RAM. Their sources
  are resolved and compiled with yours -- you never name their files.
* The **top module changes** to ``picorv32_top``, the local wrapper that
  instantiates the core and the RAM and connects them.

So ``rtl.memory`` is not a modified copy of ``rtl``; it is ``rtl`` plus a
library plus a wrapper. Swapping between the two configurations is a fileset
argument, nothing more.

:meth:`.Project.write_depgraph()` draws what a project resolved to, which is the
quickest way to confirm a design is composed the way you think it is. Call it on
a project you have added filesets to -- no run required::

   project.write_depgraph("picorv32.png")

.. scdepgraph:: picorv32_depgraph.py
   :variable: project("rtl.memory")
   :align: center

Reading down from the design: ``rtl.memory`` pulls in both ``picorv32/rtl`` and
``la_spram/rtl``, and the SRAM brings a dependency of its own that you never had
to name. The ``sdc.freepdk45`` branch is the constraint fileset added alongside
the RTL one -- change the PDK and that branch changes with it.

The graph above is drawn before ``asic_target`` is applied, so it is the design's
own shape. Call it *after* the target and the PDK, the standard cell library and
every macro library the target registers join the picture -- the honest view of a
build, and a considerably wider one.

.. note::
   This SRAM is soft -- it is RTL, synthesized along with everything else. That
   is the simplest thing that works, and it is what makes this example run on any
   of the three PDKs. A production SoC would use a **hardened** memory macro
   instead, with fixed timing and area; see
   :ref:`Instantiating a hardened module <hardened_modules>` for how a
   pre-implemented block is packaged and placed.

Results
=======

Outputs land in ``build/picorv32/job0/``. The final layout is under
``write.gds/0/outputs/``, and metrics are summarised at the end of the run by
:meth:`.Project.summary`. To open the layout:

.. code-block:: bash

   sc-show -design picorv32                        # the finished GDS
   sc-show -design picorv32 -arg_step floorplan.init   # an intermediate stage

:ref:`sc-show <app-sc-show>` needs a viewer -- :ref:`KLayout <tool-klayout>` is
the usual choice. :ref:`Directory structures <build_directory>` explains the rest
of the tree, and :ref:`Working with Metrics <dev_metrics>` covers what the
summary is showing you.

Extending Your Design
=====================

You now have the two techniques that hierarchical design rests on: pulling
sources from another repository, and composing filesets from other designs. From
here:

* :ref:`Instantiating a hardened module <hardened_modules>` -- replace the soft
  SRAM with a hardened macro.
* :ref:`Multi-Job Flows <multi_job_flows>` -- run implementation and signoff as
  separate jobs, or sweep a parameter across many.
* :ref:`Parallel Job Execution <parallel_execution>` -- run those jobs
  concurrently.
