.. _builtin_flows:

Pre-Defined Flows
====================

The following are examples are pre-built :ref:`flows <dev_flows>` that come with SiliconCompiler which you can use for your own builds.

See the pre-built :ref:`targets <builtin_targets>` for examples on how these are used in conjunction with :ref:`pdks <builtin_pdks>`, :ref:`tools <builtin_tools>` and :ref:`libraries <builtin_libraries>`.

ASIC Flows
----------

Complete ASIC compilation flows that take RTL through synthesis, place-and-route,
and finishing. The ``language`` argument selects the front-end used to bring the
design into Verilog before the shared place-and-route back-end runs; a variant is
shown below for each supported source language.

.. schema::
  :root: siliconcompiler.flows.asicflow/ASICFlow

ASIC Subflows
^^^^^^^^^^^^^

The ASIC flow is assembled from the following stage-specific subflows. They can be
used on their own to run or debug an individual stage of the back-end.

.. schema::
  :root: siliconcompiler.flows.asicflow/CleanupSynthFlow

.. schema::
  :root: siliconcompiler.flows.asicflow/FloorplanningFlow

.. schema::
  :root: siliconcompiler.flows.asicflow/PlacementFlow

.. schema::
  :root: siliconcompiler.flows.asicflow/ClockTreeSynthesisFlow

.. schema::
  :root: siliconcompiler.flows.asicflow/FillerCellFlow

.. schema::
  :root: siliconcompiler.flows.asicflow/RoutingFlow

.. schema::
  :root: siliconcompiler.flows.asicflow/MetalFillFlow

Elaboration Flows
-----------------

Front-end flows that elaborate an RTL design from its source files and emit Verilog.
Because every variant produces Verilog, they can be used interchangeably as a
front-end for any downstream flow that consumes a Verilog netlist.

.. schema::
  :root: siliconcompiler.flows.elaborationflow/ElaborationFlow

Elaboration Subflows
^^^^^^^^^^^^^^^^^^^^^

The language-specific building blocks for elaborating a design in a single
source language. They can be used on their own as a front-end.

.. schema::
  :root: siliconcompiler.flows.elaborationflow/SlangElaborationFlow

.. schema::
  :root: siliconcompiler.flows.elaborationflow/SV2VElaborationFlow

.. schema::
  :root: siliconcompiler.flows.elaborationflow/HLSElaborationFlow

.. schema::
  :root: siliconcompiler.flows.elaborationflow/VHDLElaborationFlow

.. schema::
  :root: siliconcompiler.flows.elaborationflow/ChiselElaborationFlow

.. schema::
  :root: siliconcompiler.flows.elaborationflow/BluespecElaborationFlow

Synthesis Flows
---------------

Flows that elaborate and synthesize an RTL design into a gate-level netlist. Each
variant pairs a different front-end language with the shared Yosys synthesis step.

.. schema::
  :root: siliconcompiler.flows.synflow/SynthesisFlow

Lint Flows
----------

Flows for linting an RTL design.

.. schema::
  :root: siliconcompiler.flows.lintflow/LintFlow

.. schema::
  :root: siliconcompiler.flows.lintflow/VerilatorLintFlow

.. schema::
  :root: siliconcompiler.flows.lintflow/SlangLintFlow

Design Verification Flows
-------------------------

Flows for simulating and verifying a design. Each variant targets a specific
simulator (and optionally cocotb-based testbenches).

.. schema::
  :root: siliconcompiler.flows.dvflow/DVFlow

.. schema::
  :root: siliconcompiler.flows.dvflow/IcarusDVFlow

.. schema::
  :root: siliconcompiler.flows.dvflow/IcarusCocotbDVFlow

.. schema::
  :root: siliconcompiler.flows.dvflow/VerilatorDVFlow

.. schema::
  :root: siliconcompiler.flows.dvflow/VerilatorCocotbDVFlow

.. schema::
  :root: siliconcompiler.flows.dvflow/XyceDVFlow

.. schema::
  :root: siliconcompiler.flows.dvflow/XDMXyceDVFlow

Formal Verification Flows
-------------------------

Flows for formally verifying the SVA properties in an RTL design using
SymbiYosys (sby).

.. schema::
  :root: siliconcompiler.flows.formalflow/PropertyCheckFlow

DRC Flows
---------

Flows for running design rule checking (DRC) signoff on a layout.

.. schema::
  :root: siliconcompiler.flows.drcflow/DRCFlow

.. schema::
  :root: siliconcompiler.flows.drcflow/KlayoutDRCFlow

.. schema::
  :root: siliconcompiler.flows.drcflow/MagicDRCFlow

LVS Flows
---------

Flows for running layout-versus-schematic (LVS) signoff on a layout.

.. schema::
  :root: siliconcompiler.flows.lvsflow/MagicLVSFlow

Signoff Flows
-------------

Flows that combine the physical verification steps into a single signoff flow.

.. schema::
  :root: siliconcompiler.flows.signoffflow/SignoffFlow

FPGA Flows
----------

Complete FPGA compilation flows. Each variant targets a different FPGA toolchain.

.. schema::
  :root: siliconcompiler.flows.fpgaflow/FPGANextPNRFlow

.. schema::
  :root: siliconcompiler.flows.fpgaflow/FPGAVPRFlow

.. schema::
  :root: siliconcompiler.flows.fpgaflow/FPGAVPROpenSTAFlow

.. schema::
  :root: siliconcompiler.flows.fpgaflow/FPGAXilinxFlow

Utility Flows
-------------

Supporting flows for screenshots, format conversion, parasitic extraction, and
interposer assembly.

.. schema::
  :root: siliconcompiler.flows.showflow/ShowFlow

.. schema::
  :root: siliconcompiler.flows.highresscreenshotflow/HighResScreenshotFlow

.. schema::
  :root: siliconcompiler.flows.img2streamflow/Img2StreamFlow

.. schema::
  :root: siliconcompiler.flows.generate_openroad_rcx/GenerateOpenRCXFlow

.. schema::
  :root: siliconcompiler.flows.interposerflow/InterposerFlow
