.. _own_design_tutorial:

##########################
Bringing Your Own Design
##########################

The demo builds someone else's design. This page is the next question: you have
:term:`RTL` of your own, and you want to compile it.

There are four things to tell SiliconCompiler, and nothing else is required to
start.

1. Describe the design
======================

A :class:`.Design` is a top module plus the :term:`filesets <fileset>` holding
its sources. Sources go in ``rtl``; timing constraints go in ``sdc``, separately,
because they change with the technology and the RTL does not:

.. code-block:: python

   from siliconcompiler import Design

   design = Design("mydesign")
   design.set_dataroot("root", __file__)

   with design.active_dataroot("root"), design.active_fileset("rtl"):
       design.set_topmodule("mydesign")
       design.add_file("mydesign.v")
       design.add_file("submodule.v")

   with design.active_dataroot("root"), design.active_fileset("sdc"):
       design.add_file("mydesign.sdc")

:meth:`.Design.set_dataroot` with ``__file__`` makes every path relative to the
script, so the design still builds when someone clones it somewhere else. That
is worth doing from the start -- see :ref:`dataroot <glossary>` for the other
kinds, including sources fetched from a git repository at a pinned commit.

Parameters and defines belong to the fileset too:

.. code-block:: python

   design.set_param("WIDTH", "32", fileset="rtl")
   design.add_define("SYNTHESIS", fileset="rtl")

2. Check it before you build
============================

.. code-block:: python

   assert design.check_filepaths()

Ten seconds here saves a failed run later; unresolvable paths are the most
common first failure. Then lint it, which needs no tools at all and catches the
next tier of problem:

.. code-block:: python

   from siliconcompiler import Lint
   from siliconcompiler.flows.lintflow import LintFlow

   project = Lint(design)
   project.add_fileset("rtl")
   project.set_flow(LintFlow())
   project.run()

See :ref:`Lint your RTL <lint_tutorial>`. Do not skip this: :term:`synthesis`
error messages are much worse than :term:`lint` error messages.

3. Pick a technology
====================

A :term:`target` bundles the :term:`PDK`, the :term:`standard cell` libraries and the
tool setup. Start with an open one -- you can change it later without touching
the design:

.. code-block:: python

   from siliconcompiler import ASIC
   from siliconcompiler.targets import freepdk45_demo

   project = ASIC(design)
   project.add_fileset("rtl")
   project.add_fileset("sdc")

   freepdk45_demo(project)

.. list-table::
   :header-rows: 1
   :widths: 24 76

   * - Target
     - Use when
   * - :ref:`freepdk45_demo <target-siliconcompiler-targets-freepdk45-demo>`
     - You want fast results and are not taping out. A fictional 45nm process,
       so timing numbers are indicative, not real.
   * - :ref:`skywater130_demo <target-siliconcompiler-targets-skywater130-demo>`
     - You want an open PDK that real silicon has been made in. Slower.
   * - :ref:`asap7_demo <target-siliconcompiler-targets-asap7-demo>`
     - You want to see behaviour at an advanced node. Predictive, not
       manufacturable.
   * - :ref:`gf180_demo <target-siliconcompiler-targets-gf180-demo>`, :ref:`ihp130_demo <target-siliconcompiler-targets-ihp130-demo>`
     - Other open PDKs with real foundry paths.

Constraints your design will probably need:

.. code-block:: python

   project.constraint.area.set_diearea_rectangle(500, 500, coremargin=10)

Without a die area the floorplanner picks one from a utilisation target, which
is fine until you have macros -- see
:ref:`Instantiating a hardened module <hardened_modules>`.

4. Run it
=========

.. code-block:: python

   project.run()
   project.summary()

The summary is the first thing to read, and :ref:`When a run fails
<debug_tutorial>` is the second.

Then what?
==========

The interesting part starts once it builds. Common next steps, in the order
people usually need them:

.. list-table::
   :header-rows: 1
   :widths: 38 62

   * - You want to
     - Go to
   * - Use RTL from another repository
     - :ref:`Building Your Own SoC <picorv32_example>` -- dataroots pinned to a
       commit
   * - Compose your design from another design
     - :ref:`Building Your Own SoC <picorv32_example>` -- ``add_depfileset``
   * - Use an SRAM or another hard macro
     - :ref:`Instantiating a hardened module <hardened_modules>`
   * - Try several settings and keep the best
     - :ref:`Parallel Job Execution <parallel_execution>` -- index parallelism
   * - Sweep a parameter and compare
     - :ref:`Multi-Job Flows <multi_job_sweep>`
   * - Compile from VHDL, Bluespec, Chisel or Migen
     - :ref:`Hardware design frontends <hw_frontends>`
   * - Target an FPGA instead
     - :ref:`Build for an FPGA <fpga_tutorial>`
   * - Not install any EDA tools
     - :ref:`Docker <docker>`, or a :ref:`remote run <remote_processing>`

.. seealso::
   :ref:`Example designs <examples>` -- a working script for nearly every row
   above, and :ref:`How do I…? <howto>` for the one-off questions that come up
   along the way.
