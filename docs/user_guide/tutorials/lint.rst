.. _lint_tutorial:

################
Lint Your RTL
################

Linting checks your :term:`RTL` for syntax and style problems without compiling
it, and it is the quickest way to get a real result out of SiliconCompiler. No
:term:`PDK`, no cloud account, and -- unusually -- **no EDA tools to install**.
The default linter, `slang <https://sv-lang.com>`_, ships as a Python package
that comes with SiliconCompiler itself, so this works immediately after
``pip install``.

A run takes about ten milliseconds.

The script
==========

Save this next to a Verilog file called ``blinky.v``:

.. code-block:: python

   from siliconcompiler import Design, Lint
   from siliconcompiler.flows.lintflow import LintFlow

   design = Design("blinky")
   design.set_dataroot("root", __file__)
   with design.active_dataroot("root"), design.active_fileset("rtl"):
       design.set_topmodule("blinky")
       design.add_file("blinky.v")

   project = Lint(design)
   project.add_fileset("rtl")
   project.set_flow(LintFlow())

   project.run()
   project.summary()

The shape is the same as every other SiliconCompiler script -- describe the
design, pick a :term:`flow`, run -- with two differences: the project type is
:class:`.Lint` rather than :class:`.ASIC`, and no :ref:`target <builtin_targets>`
is loaded, because there is no technology to target.

What it tells you
=================

On clean sources the run says so and stops:

.. code-block:: text

   | INFO     | job0 | lint | 0 | Number of errors: 0
   | INFO     | job0 | lint | 0 | Number of warnings: 0
   | INFO     | job0 | lint | 0 | Finished task in 0.01s

Give it something broken -- a mistyped signal name and an out-of-range bit
select -- and you get the diagnosis with the source line:

.. code-block:: text

   | ERROR | blinky.v:13:24: error: use of undeclared identifier 'count'
   | ERROR |             counter <= count + 1'b1;
   | ERROR |                        ^~~~~
   | ERROR | blinky.v:14:32: warning: cannot refer to element 8 of 'reg[7:0]' [-Windex-oob]
   | ERROR |             led     <= counter[N];
   | ERROR |                                ^
   | INFO  | Number of errors: 2

Both counts are recorded as :term:`metrics <metric>` -- :keypath:`metric,errors`
and :keypath:`metric,warnings` -- so they appear in
:meth:`.Project.summary()` and can be read back the same way as any other
result:

.. code-block:: python

   project.get("metric", "errors", step="lint", index="0")

That is what makes linting worth scripting rather than running by hand: the
result is a number you can gate on.

Choosing the linter
===================

:ref:`LintFlow <schema-siliconcompiler-flows-lintflow-lintflow>` takes a ``tool`` argument:

.. code-block:: python

   project.set_flow(LintFlow())                      # slang (default)
   project.set_flow(LintFlow(tool="verilator"))      # verilator
   project.set_flow(LintFlow(tool="all"))            # both, as separate nodes

``slang`` needs nothing installed. ``verilator`` is an
:ref:`external tool <external_tools>` and has to be available on your machine,
but it catches a different class of problem, which is what ``tool="all"`` is
for -- it builds one node per linter and runs them side by side.

The lint script above passes ``-Weverything`` to slang, so you are seeing
everything it has to say.

In a real build script
======================

``examples/heartbeat`` exposes linting as one target among many, so the same
design can be linted, synthesized, simulated or hardened without editing
anything:

.. literalinclude:: examples/heartbeat/make.py
   :language: python
   :pyobject: lint

.. code-block:: bash

   cd examples/heartbeat
   smake lint            # or: smake lint --N 16

See :ref:`Run a build script's targets without editing it <howto_smake>` for how
that works, and :ref:`Example designs <examples>` for the rest of what this one
can do.

Next
====

* :ref:`Simulate your design <simulate_tutorial>` -- the next cheapest check,
  and still no PDK.
* :ref:`Quickstart <quickstart_guide>` -- the same design taken all the way to
  a layout.
* :ref:`How do I…? <howto>` -- recipes for the things you will want next.
