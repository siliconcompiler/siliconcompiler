.. _commercial_tools:

##########################
Using Commercial Tools
##########################

SiliconCompiler drives commercial EDA tools as well as open-source ones -- the
:term:`flowgraph` does not care which tool a :term:`task` wraps. What differs is how you get the
driver.

.. important::
   **Read this first, because the capability tables do not say it.**
   :ref:`Vivado <tool-vivado>` is the only commercial tool whose driver ships in
   this repository. Drivers for the Synopsys, Cadence and Siemens tools exist and
   are in use, but cannot be distributed publicly: a tool driver encodes command
   lines, script structure and flow knowledge that vendor agreements cover.

   So "supported" means the integration exists, not that ``pip install``
   gives it to you. If you need one of those, ask on
   `Discussions <https://github.com/siliconcompiler/siliconcompiler/discussions>`_ --
   that is the honest route, and it is a conversation about access rather than
   something the docs can settle.

Everything else you can drive yourself, using the same mechanisms the built-in
drivers use.

Vivado, end to end
==================

``examples/heartbeat`` targets a Xilinx Artix-7 alongside its :term:`ASIC` flows:

.. literalinclude:: examples/heartbeat/make.py
   :language: python
   :pyobject: fpga

.. code-block:: bash

   cd examples/heartbeat
   smake fpga

:ref:`FPGAXilinxFlow <schema-siliconcompiler-flows-fpgaflow-fpgaxilinxflow>` is
the standard Vivado pipeline. SiliconCompiler runs ``vivado`` in batch mode, so
it has to be on your ``PATH`` and your licence has to work -- test that outside
SiliconCompiler first, because a licence failure surfaces as a tool error in
``<step>.log`` rather than as anything more helpful.

Injecting Tcl around a tool
===========================

The most common commercial-tool request is not a new driver at all: it is *"I
need to run my own Tcl at a specific point"* -- a vendor-specific constraint, an
in-house checking script, an extra report.

Every task takes a pre- and post-script, so you do not have to fork the driver:

.. code-block:: python

   from siliconcompiler.tools.vivado.syn_fpga import SynthesisTask

   task = SynthesisTask.find_task(project)
   task.add_prescript("scripts/my_setup.tcl")     # before the tool's own script
   task.add_postscript("scripts/my_reports.tcl")  # after it

The scripts are sourced by the tool in its own interpreter, with the tool's state
already loaded -- so a post-script sees the elaborated or placed design and can
report on it. Both are per-node, so ``step=``/``index=`` narrows them to one
point in the flow:

.. code-block:: python

   task.add_postscript("scripts/check.tcl", step="synthesis")

That is the answer to "how do I get my Tcl between synthesis and
implementation": attach it to the step it belongs after.

Writing a driver
================

For a tool with no driver at all, a :term:`task` class is the unit of work.
:ref:`Building a Tool <dev_tools>` is the reference; the shape is four optional
methods:

.. list-table::
   :header-rows: 1
   :widths: 24 76

   * - Method
     - Does
   * - :meth:`~.Task.setup`
     - Declares what the task needs and produces -- inputs, outputs, required
       files, the tool and version
   * - :meth:`~.Task.pre_process`
     - Runs before the tool: stage files, generate a script
   * - :meth:`~.Task.runtime_options`
     - Builds the command line
   * - :meth:`~.Task.post_process`
     - Reads the tool's reports and records :term:`metrics <metric>`

:meth:`~.Task.post_process` is the one people underestimate. A driver that runs a tool but
records no metrics gives you a build you cannot gate on -- no
:ref:`checklist <checklists>` can check it, and the summary table has nothing to
show. Read an existing driver before writing yours; the OpenROAD and Yosys ones
are the most complete.

Keeping it private
==================

A driver for a licensed tool usually cannot go in this repository, and it does
not need to. Package it as your own ``pip``-installable module and register it
through entry points --
:ref:`Packaging an External Library <dev_external_libraries>` covers the layout,
the ``pyproject.toml``, a proprietary licence identifier, and the
environment-variable :term:`dataroot` pattern for reference data that must not
enter a wheel.

:ref:`Where does my module go? <module_placement>` is the one-page version of
that decision.

.. seealso::
   :ref:`Authoring a Custom Flow <custom_flow_tutorial>` for wiring a new task
   into a pipeline, and :ref:`When a Run Fails <debug_tutorial>` for reading a
   tool's log when it does not do what you expected.
