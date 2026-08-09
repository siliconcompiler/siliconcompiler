.. _simulate_tutorial:

######################
Simulate and Verify
######################

Between :ref:`linting <lint_tutorial>` and building a layout sits everything
that checks the design actually *works*. SiliconCompiler drives three kinds of
check, none of which needs a :term:`PDK`:

.. list-table::
   :header-rows: 1
   :widths: 22 30 48

   * - Check
     - Project type and flow
     - Answers
   * - **Simulation**
     - :class:`.Sim` + :ref:`DVFlow <schema-siliconcompiler-flows-dvflow-dvflow>`
     - "Does it do the right thing on the stimulus I wrote?"
   * - **cocotb**
     - :class:`.Sim` + :ref:`dvflow_cocotb <target-siliconcompiler-targets-dvflow-cocotb>`
     - The same, with the testbench written in Python
   * - **Formal**
     - :class:`.Sim` + :ref:`PropertyCheckFlow <schema-siliconcompiler-flows-formalflow-propertycheckflow>`
     - "Is this property true for *every* input, not just the ones I tried?"

All three are :class:`.Sim` projects: the project type says what kind of question
you are asking, and the flow says which tool answers it.

Simulation
==========

A :class:`.Sim` project needs one thing an :class:`.ASIC` project does not: a
:term:`testbench`. It goes in its own :term:`fileset` alongside the :term:`RTL`, so the same
design object serves both.

.. literalinclude:: examples/heartbeat/make.py
   :language: python
   :pyobject: sim

Two things are worth pulling out:

* **The testbench is a fileset, not a special case.** ``testbench.verilator.v``
  and ``testbench.icarus.v`` are ordinary :term:`filesets <fileset>`, so switching simulators is
  switching which one you add.
* **The tool is chosen by the flow.** :ref:`DVFlow <schema-siliconcompiler-flows-dvflow-dvflow>` takes ``tool=`` --
  ``icarus``, ``verilator``, ``xyce`` and ``xdm-xyce`` are supported -- and
  ``np=`` to run several independent pipelines at once for constrained-random
  stimulus.

Both simulators are :ref:`external tools <external_tools>`. Icarus is the
smaller install; Verilator is faster on large designs and is what the
``.cc`` testbench variants target.

Run it from the example:

.. code-block:: bash

   cd examples/heartbeat
   smake sim                        # verilator, Verilog testbench
   smake sim --tool icarus

The waveform lands in the node's ``reports`` directory as a :term:`VCD`, and the target
above opens it for you.

.. seealso::
   ``smake sim_postpnr`` in the same script simulates the **gate-level netlist**
   after place-and-route, against the Skywater130 cell models -- the check that
   the implemented design still matches the RTL. ``smake power`` then chains
   three jobs to turn that simulation's VCD into a vector-driven power number.

Python testbenches with cocotb
==============================

`cocotb <https://www.cocotb.org>`_ writes the testbench in Python instead of
Verilog, driving the simulator from a coroutine. SiliconCompiler wires it up
through the :ref:`dvflow_cocotb <target-siliconcompiler-targets-dvflow-cocotb>` target rather than a hand-built flow:

.. literalinclude:: examples/adder_cocotb/make.py
   :language: python
   :pyobject: sim_icarus

The helper registers both the Icarus and Verilator cocotb flows and selects
Icarus; ``project.set_flow("verilatorcocotbdvflow")`` switches to the other
without rebuilding anything.

``cocotb`` itself installs from PyPI (``pip install siliconcompiler[cocotb]``),
so the only external dependency is the simulator underneath it.
:ref:`examples/adder_cocotb <example-adder_cocotb>` is the complete design.

Formal property checking
========================

Simulation shows a property holds for the stimulus you wrote. Formal checking
asks whether it holds at all. :ref:`PropertyCheckFlow <schema-siliconcompiler-flows-formalflow-propertycheckflow>` drives
`SymbiYosys <https://github.com/YosysHQ/sby>`_ over SVA assertions in three
modes:

.. list-table::
   :header-rows: 1
   :widths: 18 82

   * - Mode
     - Asks
   * - ``BMC``
     - Is the assertion true for the first *N* cycles? (bounded model check)
   * - ``PROVE``
     - Is it true in every reachable state? (unbounded, by k-induction)
   * - ``COVER``
     - Is this condition reachable *at all*?

Each mode becomes its own node, so asking several questions at once runs them in
parallel:

.. code-block:: python

   from siliconcompiler.flows.formalflow import PropertyCheckFlow, PropertyCheckMode

   project.set_flow(PropertyCheckFlow(
       modes=PropertyCheckMode.BMC | PropertyCheckMode.PROVE | PropertyCheckMode.COVER))

:ref:`examples/sva_sby <example-sva_sby>` has one script per mode, and a FIFO
carrying named assertions that runs all three. The first three mirror the
official SymbiYosys quickstart, so they are directly comparable with its
``.sby`` files.

Requires ``sby`` and ``yosys``; no PDK.

Next
====

* :ref:`Quickstart <quickstart_guide>` -- take a checked design to a layout.
* :ref:`Example designs <examples>` -- the complete scripts behind each section
  above.
* :ref:`Working with Metrics <dev_metrics>` -- reading results back out of a run.
