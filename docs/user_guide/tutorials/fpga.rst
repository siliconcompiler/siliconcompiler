.. _fpga_tutorial:

######################
Build for an FPGA
######################

SiliconCompiler compiles to FPGA bitstreams as well as to :term:`GDSII`, through the
same schema, the same :term:`flowgraph` and the same run. What changes is the project
type, the thing you target, and the artifact you get back.

For a lot of readers this is the easier on-ramp: an FPGA flow needs no :term:`PDK`, no
foundry agreement and no tapeout budget, and the open-source toolchain for
Lattice iCE40 parts is a package-manager install away.

.. list-table::
   :header-rows: 1
   :widths: 26 37 37

   * -
     - ASIC
     - FPGA
   * - Project type
     - :class:`.ASIC`
     - :class:`.FPGA`
   * - What you target
     - a :ref:`PDK <builtin_pdks>` and standard cell libraries
     - an :class:`.FPGADevice` -- one part
   * - How you target it
     - ``target(project)``
     - ``project.set_fpga(...)``
   * - Extra constraints
     - SDC timing constraints
     - SDC, plus a pin-assignment file (PCF/XDC)
   * - Output
     - GDSII
     - a bitstream

Check your install first
========================

The FPGA equivalent of the :ref:`ASIC demo <asic_demo>` builds an 8-bit counter
onto a small open architecture called **z1000**:

.. code-block:: bash

   python -m siliconcompiler.demos.fpga_demo

It runs Yosys for synthesis, `VPR <https://docs.verilogtorouting.org>`_ for
place-and-route and OpenSTA for timing, so a clean run tells you that half of
your toolchain is working. z1000 is a demo architecture -- 2K :term:`LUTs <LUT>`, no hard
macros -- and exists to be a self-test, not a part you would ship to.

A real part: blinky on an iCE40
===============================

:ref:`examples/blinky <example-blinky>` builds a :term:`bitstream` for a Lattice
iCE40 UP5K, the part on an `iCEBreaker
<https://github.com/icebreaker-fpga/icebreaker>`_ board:

.. literalinclude:: examples/blinky/blinky.py
   :language: python
   :start-after: # Create a design schema to hold the project's configuration.
   :end-before: # --- Execution & Analysis ---
   :dedent: 4

Three things differ from an ASIC script:

* **A second constraint fileset.** ``pcf`` is a :term:`fileset` holding the pin-constraint file, which
  maps ports in your Verilog onto physical pins on the package. Without it the
  tools have no idea where ``led`` goes.
* **A device instead of a target.** :meth:`.FPGA.set_fpga` takes an
  :class:`.FPGADevice` -- here ``ICE40Up5k_sg48``, shipped in
  ``siliconcompiler.fpgas``. The device carries the architecture description,
  the primitives Yosys may map to and the timing models, which is what a PDK plus
  a cell library does on the ASIC side.
* **An FPGA flow.** :ref:`FPGANextPNRFlow <schema-siliconcompiler-flows-fpgaflow-fpganextpnrflow>` is Yosys plus
  `nextpnr <https://github.com/YosysHQ/nextpnr>`_ plus ``icepack``.

Run it:

.. code-block:: bash

   cd examples/blinky
   python blinky.py

The summary reports resource utilisation -- LUTs, flip-flops, carry cells --
rather than cell area, because those are the numbers that decide whether a
design fits.

Which flow
==========

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Flow
     - Tools
     - For
   * - :ref:`FPGANextPNRFlow <schema-siliconcompiler-flows-fpgaflow-fpganextpnrflow>`
     - yosys, nextpnr, icepack
     - Lattice iCE40 and similar open-toolchain parts
   * - :ref:`FPGAVPRFlow <schema-siliconcompiler-flows-fpgaflow-fpgavprflow>`
     - yosys, VPR
     - Research and custom architectures described in VPR's XML
   * - :ref:`FPGAVPROpenSTAFlow <schema-siliconcompiler-flows-fpgaflow-fpgavpropenstaflow>`
     - the above, plus OpenSTA
     - The same, when you also want timing analysis
   * - :ref:`FPGAXilinxFlow <schema-siliconcompiler-flows-fpgaflow-fpgaxilinxflow>`
     - Vivado
     - Xilinx parts; needs a Vivado licence

``examples/heartbeat`` carries a Xilinx target alongside its ASIC ones, so the
same design goes to an Artix-7 with ``smake fpga``.

Installing the tools
====================

``sc-install`` has an FPGA group:

.. code-block:: bash

   sc-install -group fpga

That covers ``yosys``, ``nextpnr``, ``icepack`` and ``vpr``. See
:ref:`External Tools <external_tools>` for what is script-installable on your
platform, and :ref:`Docker <docker>` to skip installing entirely. Vivado is a
vendor tool and has to be installed and licensed separately.

Defining your own device
========================

:class:`.FPGADevice` is a library -- it derives from the same base as a standard
cell library -- so describing a new part is the job covered by
:ref:`Defining a Library <dev_libraries>`, and packaging one to share is
:ref:`Packaging an External Library <dev_external_libraries>`.

For a complete worked device, read ``siliconcompiler/demos/fpga_demo.py``: ``Z1000``
sets the :term:`LUT` size, the register types Yosys may infer, the VPR architecture and
routing-graph files, and the Liberty models OpenSTA reads.

Next
====

* :ref:`Lint your RTL <lint_tutorial>` -- faster still, and needs nothing
  installed.
* :ref:`Example designs <examples>` -- ``blinky`` and the rest, with what each
  one needs.
* :ref:`Compilation Process <execution_model>` -- how a flow is put together, if
  you want to build your own.
