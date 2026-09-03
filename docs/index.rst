##################################################
Welcome to SiliconCompiler's Documentation!
##################################################

.. toctree::
   :maxdepth: 1
   :hidden:

   user_guide/index
   Development Guide <development_guide/index>
   reference_manual/index
   Contributing <development_guide/contribution>

**Version**:
|version|

**Useful Links**:
:ref:`What is SiliconCompiler? <what_is_sc>` | :ref:`Installation <installation>` | `GitHub Repo <https://github.com/siliconcompiler/siliconcompiler>`_ | `File an Issue <https://github.com/siliconcompiler/siliconcompiler/issues>`_

SiliconCompiler is an open source, modular build system that automates translation
from hardware design source code to silicon ("make for silicon").


###################################
Getting started
###################################

.. container:: sc-quad

   .. container:: sc-card

      **New here?**

      :ref:`Install it <installation>`, then :ref:`run the demo <quickstart_guide>`
      -- :term:`RTL` to :term:`GDS <GDSII>` in thirteen lines.
      :ref:`What is SiliconCompiler? <what_is_sc>`

   .. container:: sc-card

      **Bringing your own design?**

      The :ref:`User Guide <user_guide>` runs pre-defined flows on your own RTL.
      Start by :ref:`bringing your own design <own_design_tutorial>`, or
      :ref:`lint it <lint_tutorial>` first -- no EDA tools needed.

   .. container:: sc-card

      **Looking something up?**

      The :ref:`Reference Manual <reference_manual>` has the
      :ref:`schema <schema>` and the :ref:`Python API <schema_api>`.
      :ref:`How do I...? <howto>` and the :ref:`FAQ <faq>` answer by task.

   .. container:: sc-card

      **Extending SiliconCompiler?**

      The :ref:`Development Guide <development_guide>` covers your own tools,
      flows, targets, PDKs and libraries, and
      :ref:`packaging them <dev_external_libraries>`.
      :ref:`Contributing <contributing>` covers review.


###################################
I want to...
###################################

Every page below is one click from here, grouped by what you are trying to do.

Get something running
---------------------

* :ref:`Install SiliconCompiler <installation>` -- ``pip install siliconcompiler``, plus the tools a local flow needs.
* :ref:`Run the demo build <quickstart_guide>` -- RTL to GDS, walked through line by line.
* :ref:`Check my RTL for mistakes <lint_tutorial>` -- the quickest thing to try: the default linter needs no EDA tools at all.
* :ref:`Simulate, or prove a property formally <simulate_tutorial>` -- Verilator, Icarus, cocotb, and viewing the waveform.
* :ref:`Build my own design <own_design_tutorial>` -- what to change when the design is yours.
* :ref:`Work out why a run failed <debug_tutorial>` -- reading logs, metrics and the failing node.

Run it somewhere else
---------------------

* :ref:`Run remotely <remote_processing>` -- compile against a server you or your organization operates.
* :ref:`Run inside a container <docker>` -- the supported route on Windows.
* :ref:`Run steps in parallel <parallel_execution>` -- more than one node at a time.
* :ref:`Run on a cluster <cluster_tutorial>` -- Slurm and friends.
* :ref:`Run builds in CI <ci_tutorial>` -- keeping a design building on every commit.
* :ref:`Watch a build while it runs <dashboard_tutorial>` -- the web dashboard.
* :ref:`Get an email when a job finishes <emails>` -- job status notifications.

Take a design further
---------------------

* :ref:`Build an SoC with a memory <picorv32_example>` -- a processor and an SRAM macro.
* :ref:`Target an FPGA <fpga_tutorial>` -- :term:`bitstreams <bitstream>` instead of masks.
* :ref:`Wrap a design in an IO pad ring <padring_tutorial>` -- pads, corners, bond pads and a core power grid.
* :ref:`Reuse a block that is already hardened <hardened_modules>` -- instantiating a macro.
* :ref:`Harden a parameterized module <uniquify_modules>` -- one module, several configurations.
* :ref:`Write RTL in something other than Verilog <hw_frontends>` -- Chisel, Migen/Amaranth, Bluespec and more.
* :ref:`Turn a machine learning model into silicon <soda_tutorial>` -- MLIR in, GDSII out, via SODA Synthesizer.
* :ref:`Improve the parasitic estimate <pex_calibration>` -- calibrating against a golden extraction.
* :ref:`Sweep a parameter across many jobs <multi_job_flows>` -- multi-job flows and automation.
* :ref:`Build my own flow <custom_flow_tutorial>` -- wiring tasks into a graph of your own.
* :ref:`Use commercial tools <commercial_tools>` -- Synopsys, Cadence and Siemens flows.
* :ref:`Browse the example designs <examples>` -- every example in the repository, built and pictured.

When something is wrong
-----------------------

* :ref:`Frequently asked questions <faq>` -- the questions that come up most.
* :ref:`How do I...? <howto>` -- a task-oriented index of the calls you need.
* :ref:`Look up a term <glossary>` -- the glossary.
* :ref:`Port code written against the Chip API <migration_guide>` -- ``Chip`` was removed in 0.35.0; this maps the old calls to the current ones.
* `File an issue <https://github.com/siliconcompiler/siliconcompiler/issues>`_ -- if you cannot find something, or something is not working, the SiliconCompiler team is happy to help.

Extend it
---------

* :ref:`Add a tool, flow, target, PDK or library <development_guide>` -- the Development Guide.
* :ref:`Package a library so others can install it <dev_external_libraries>` -- turning modules into a ``pip``-installable distribution.
* :ref:`Contribute to SiliconCompiler <contributing>` -- where a new module belongs, and how to get it reviewed.


###################################
Supported technologies
###################################

.. include:: user_guide/include/supported_technologies.inc


###################################
Authors
###################################

.. include:: user_guide/include/authors.inc
