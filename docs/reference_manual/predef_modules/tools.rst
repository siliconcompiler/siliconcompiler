.. _builtin_tools:

Pre-Defined Tools
===================

The following are examples of pre-built :ref:`tool <tools>` drivers that come with SiliconCompiler which you can use for your own builds.

.. rst-class:: page-break

See the pre-built :ref:`targets <builtin_targets>` for examples on how these are used in conjunction with :ref:`pdks <builtin_pdks>`, :ref:`flows <builtin_flows>` and :ref:`libraries <builtin_libraries>`.

.. sctool::
  :root: siliconcompiler.tools.bambu
  :tasks: convert/ConvertTask

.. sctool::
  :root: siliconcompiler.tools.bluespec
  :tasks: convert/ConvertTask

.. sctool::
  :root: siliconcompiler.tools.builtin
  :tasks: join/JoinTask maximum/MaximumTask minimum/MinimumTask mux/MuxTask nop/NOPTask verify/VerifyTask

.. sctool::
  :root: siliconcompiler.tools.chisel
  :tasks: convert/ConvertTask

.. sctool::
  :root: siliconcompiler.tools.execute
  :tasks: exec_input/ExecInputTask

.. sctool::
  :root: siliconcompiler.tools.genfasm
  :tasks: bitstream/BitstreamTask

.. sctool::
  :root: siliconcompiler.tools.ghdl
  :tasks: convert/ConvertTask

.. sctool::
  :root: siliconcompiler.tools.graphviz
  :tasks: show/ShowTask screenshot/ScreenshotTask

.. sctool::
  :root: siliconcompiler.tools.gtkwave
  :tasks: show/ShowTask

.. sctool::
  :root: siliconcompiler.tools.icarus
  :tasks: compile/CompileTask

.. sctool::
  :root: siliconcompiler.tools.icepack
  :tasks: bitstream/BitstreamTask

.. sctool::
  :root: siliconcompiler.tools.klayout
  :tasks: convert_drc_db/ConvertDRCDBTask drc/DRCTask export/ExportTask operations/OperationsTask screenshot/ScreenshotTask show/ShowTask

.. sctool::
  :root: siliconcompiler.tools.magic
  :tasks: drc/DRCTask extspice/ExtractTask

.. sctool::
  :root: siliconcompiler.tools.montage
  :tasks: tile/TileTask

.. sctool::
  :root: siliconcompiler.tools.netgen
  :tasks: lvs/LVSTask

.. sctool::
  :root: siliconcompiler.tools.nextpnr
  :tasks: apr/APRTask

.. sctool::
  :root: siliconcompiler.tools.openroad
  :tasks: clock_tree_synthesis/CTSTask detailed_placement/DetailedPlacementTask detailed_route/DetailedRouteTask endcap_tapcell_insertion/EndCapTapCellTask fillercell_insertion/FillCellTask fillmetal_insertion/FillMetalTask global_placement/GlobalPlacementTask global_route/GlobalRouteTask init_floorplan/InitFloorplanTask macro_placement/MacroPlacementTask metrics/MetricsTask pin_placement/PinPlacementTask power_grid/PowerGridTask rcx_bench/ORXBenchTask rcx_extract/ORXExtractTask rdlroute/RDLRouteTask repair_design/RepairDesignTask repair_timing/RepairTimingTask screenshot/ScreenshotTask show/ShowTask write_data/WriteViewsTask

.. sctool::
  :root: siliconcompiler.tools.opensta
  :tasks: timing/TimingTask timing/FPGATimingTask

.. sctool::
  :root: siliconcompiler.tools.slang
  :tasks: elaborate/Elaborate lint/Lint

.. sctool::
  :root: siliconcompiler.tools.surelog
  :tasks: parse/ElaborateTask

.. sctool::
  :root: siliconcompiler.tools.surfer
  :tasks: show/ShowTask

.. sctool::
  :root: siliconcompiler.tools.sv2v
  :tasks: convert/ConvertTask

.. sctool::
  :root: siliconcompiler.tools.verilator
  :tasks: compile/CompileTask lint/LintTask

.. sctool::
  :root: siliconcompiler.tools.vivado
  :tasks: bitstream/BitstreamTask place/PlaceTask route/RouteTask syn_fpga/SynthesisTask

.. sctool::
  :root: siliconcompiler.tools.vpr
  :tasks: place/PlaceTask route/RouteTask screenshot/ScreenshotTask show/ShowTask

.. sctool::
  :root: siliconcompiler.tools.xdm
  :tasks: convert/ConvertTask

.. sctool::
  :root: siliconcompiler.tools.xyce
  :tasks: simulate/SimulateTask

.. sctool::
  :root: siliconcompiler.tools.yosys
  :tasks: lec_asic/ASICLECTask syn_asic/ASICSynthesis syn_fpga/FPGASynthesis
