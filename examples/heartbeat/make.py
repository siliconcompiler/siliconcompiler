#!/usr/bin/env python3
# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

from typing import Optional

from siliconcompiler import Design, FPGADevice, Flowgraph
from siliconcompiler import Lint, Sim
from siliconcompiler import ASIC, FPGA

from siliconcompiler.flows.lintflow import LintFlow
from siliconcompiler.flows.dvflow import DVFlow
from siliconcompiler.flows.fpgaflow import FPGAXilinxFlow
from siliconcompiler.flows.highresscreenshotflow import HighResScreenshotFlow

from siliconcompiler.targets import asic_target, skywater130_demo
from siliconcompiler.tools.verilator.compile import CompileTask
from siliconcompiler.tools.builtin.importfiles import ImportFilesTask
from siliconcompiler.tools.klayout.screenshot import ScreenshotTask
from siliconcompiler.tools.opensta.timing import TimingTask
from siliconcompiler.tools.slang.utils.macro import Uniquified


class HeartbeatDesign(Design):
    """Heartbeat design schema setup.

    This class defines the project structure for the 'heartbeat' design,
    configuring source files, parameters, and constraints for various

    tool flows and technology targets. By encapsulating the design setup,
    it allows for easy reuse across different flows (lint, sim, asic, fpga).
    """
    def __init__(self):
        """Initializes the HeartbeatDesign object.

        This method sets up all the necessary filesets for RTL,
        simulation testbenches (Icarus and Verilator), and technology-specific
        constraint files (SDC for ASIC, XDC for FPGA).
        """
        super().__init__()
        # Set the design's name.
        self.set_name("heartbeat")

        # Establish the root directory for all design-related files.
        self.set_dataroot("heartbeat", __file__)

        # Configure filesets within the established data root.
        with self.active_dataroot("heartbeat"):
            # RTL sources
            with self.active_fileset("rtl"):
                self.set_topmodule("heartbeat")
                self.add_file("heartbeat.v")
                self.set_param("N", "8")  # Default parameter value

            # Testbench for Icarus Verilog
            with self.active_fileset("testbench.icarus.v"):
                self.set_topmodule("heartbeat_tb")
                self.add_file("testbench.v")
                self.set_param("N", "8")

            # C++ Testbench for Verilator
            with self.active_fileset("testbench.verilator.cc"):
                self.set_topmodule("heartbeat")
                self.add_file("testbench.cc")
                self.set_param("N", "8")

            # Verilog Testbench for Verilator
            with self.active_fileset("testbench.verilator.v"):
                self.set_topmodule("heartbeat_tb")
                self.add_file("testbench.v")
                self.set_param("N", "8")

            # ASIC timing constraints for the FreePDK45 technology.
            with self.active_fileset("sdc.freepdk45"):
                self.add_file("heartbeat.sdc")

            # ASIC timing constraints for the ASAP7 technology.
            with self.active_fileset("sdc.asap7"):
                self.add_file("heartbeat_asap7.sdc")

            # ASIC timing constraints for the Skywater130 technology
            # (the generic clock constraints are reused).
            with self.active_fileset("sdc.skywater130"):
                self.add_file("heartbeat.sdc")

            # FPGA timing and pin constraints for a Xilinx Artix-7 device.
            with self.active_fileset("fpga.xc7a100tcsg324"):
                self.add_file("heartbeat.xdc")


def uniquify_heartbeat(design: Optional[HeartbeatDesign] = None) -> Uniquified:
    """Uniquify the parameterized ``heartbeat`` module of ``design``.

    This replaces the hand-written ``heartbeat8.v``/``testbench8.v``. A hardened
    macro has no parameters, so a post-synthesis netlist named ``heartbeat`` has
    no ``N`` and the parameterized testbench (``heartbeat #(.N(8))``) cannot bind
    to it. uniquify solves that: it elaborates the parameterized ``heartbeat``
    (``N`` defaults to 8 in the ``rtl`` fileset) and registers filesets for

    * ``rtl.hardened.heartbeat__N8`` -- a parameter-free variant to harden, and
    * ``rtl.heartbeat.wrapper`` -- a wrapper that keeps the ``N`` parameter and
      forwards to the variant, so the regular ``testbench.v`` binds to the
      hardened netlist.

    Args:
        design (HeartbeatDesign, optional): Design to uniquify (mutated in place
            with the new filesets). A fresh one is created if omitted.

    Returns:
        Uniquified: The handle managing the wrapper/variant filesets and builds.
    """
    return Uniquified(design or HeartbeatDesign(), ["heartbeat"], filesets=["rtl"])


def lint(N: Optional[str] = None):
    """Runs the linting flow on the Heartbeat design.

    Linting checks the Verilog source code for syntax errors and style
    issues without performing a full synthesis.

    Args:
        N (str, optional): The value for the Verilog parameter 'N'.
            Defaults to None, which uses the value set in the design schema.
    """
    # Create a project instance tailored for linting.
    project = Lint()

    # Instantiate the design configuration.
    hb = HeartbeatDesign()

    # Associate the design with the project.
    project.set_design(hb)
    # Add the necessary fileset for this flow.
    project.add_fileset("rtl")

    # Optionally override the 'N' parameter from the command line.
    if N is not None:
        hb.set_param("N", N, fileset="rtl")

    # Configure the project to use the linting flow.
    project.set_flow(LintFlow())

    # Execute the flow.
    project.run()
    # Display a summary of the results.
    project.summary()


def syn(pdk: str = "freepdk45", N: Optional[str] = None):
    """Runs the synthesis flow for the Heartbeat design.

    Synthesis converts the RTL Verilog code into a gate-level netlist
    using a specific Process Design Kit (PDK).

    Args:
        pdk (str, optional): The process design kit (PDK) to target.
            Defaults to "freepdk45".
        N (str, optional): The value for the Verilog parameter 'N'.
            Defaults to None, which uses the value set in the design schema.
    """
    # Create a project instance for an ASIC flow.
    project = ASIC()

    # Instantiate and configure the design.
    hb = HeartbeatDesign()
    project.set_design(hb)

    # Add the RTL source files and the technology-specific constraint files.
    project.add_fileset("rtl")
    project.add_fileset(f"sdc.{pdk}")

    # Optionally override the 'N' parameter.
    if N is not None:
        hb.set_param("N", N, fileset="rtl")

    # Load the target configuration for the specified PDK.
    asic_target(project, pdk=pdk)
    # Specify the synthesis flow.
    project.set_flow("synflow")

    # Run the flow and display the summary.
    project.run()
    project.summary()


def asic(pdk: str = "freepdk45", N: Optional[str] = None, jobname: Optional[str] = None,
         fileset: str = "rtl"):
    """Runs the full ASIC implementation flow for the Heartbeat design.

    This flow includes synthesis, floorplanning, placement, clock tree synthesis,
    and routing. It concludes by saving a snapshot of the final design layout.

    Args:
        pdk (str, optional): The process design kit (PDK) to target.
            Defaults to "freepdk45".
        N (str, optional): The value for the Verilog parameter 'N'.
            Defaults to None, which uses the value set in the design schema.
        jobname (str, optional): The name of the job.
        fileset (str, optional): The RTL fileset to implement. Defaults to "rtl".
    """
    # Create a project instance for an ASIC flow.
    project = ASIC()

    # Instantiate and configure the design.
    hb = HeartbeatDesign()
    project.set_design(hb)

    # Add the necessary filesets.
    project.add_fileset(fileset)
    project.add_fileset(f"sdc.{pdk}")

    # Optionally override the 'N' parameter.
    if N is not None:
        hb.set_param("N", N, fileset=fileset)

    # Load the target, which automatically selects the default 'asicflow'.
    asic_target(project, pdk=pdk)

    # Set the jobname, if specified
    if jobname:
        project.option.set_jobname(jobname)

    # Run the full place-and-route flow.
    project.run()
    # Display a summary of timing, power, and area results.
    project.summary()
    # Save the final layout and project configuration.
    project.snapshot()


def sim(N: Optional[str] = None, tool: str = "verilator", tb_type: str = "v"):
    """Runs a simulation of the Heartbeat design.

    After the simulation completes, it attempts to open the generated
    waveform file (VCD) for viewing.

    Args:
        N (str, optional): The value for the Verilog parameter 'N'.
            Defaults to None, which uses the value set in the design schema.
        tool (str, optional): The simulation tool to use ('verilator' or
            'icarus'). Defaults to "verilator".
        tb_type (str, optional): The file extension of the testbench ('cc' or
            'v'). Defaults to "v".
    """
    # Create a project instance tailored for simulation.
    project = Sim()

    # Instantiate and configure the design.
    hb = HeartbeatDesign()
    project.set_design(hb)

    # Add the tool-specific testbench and the RTL design files.
    project.add_fileset(f"testbench.{tool}.{tb_type}")
    project.add_fileset("rtl")
    # Set the appropriate design verification flow.
    project.set_flow(DVFlow(tool=tool))

    # Optionally override the 'N' parameter for the testbench.
    if N is not None:
        hb.set_param("N", N, fileset=f"testbench.{tool}.{tb_type}")

    if tool == "verilator":
        # Add trace to verilator
        CompileTask.find_task(project).set_verilator_trace(True)
        if tb_type == "v":
            CompileTask.find_task(project).set_verilator_main(True)

    # Run the simulation.
    project.run()
    project.summary()

    vcd = None
    if tool == "icarus" or (tool == "verilator" and tb_type != "cc"):
        # Find the VCD (Value Change Dump) waveform file from the results.
        vcd = project.find_result(step='simulate', index='0',
                                  directory="reports",
                                  filename="heartbeat_tb.vcd")
    else:
        # Find the VCD (Value Change Dump) waveform file from the results.
        vcd = project.find_result(step='simulate', index='0',
                                  directory="reports",
                                  filename="heartbeat.vcd")
    # If a VCD file is found, open it with the default waveform viewer.
    if vcd:
        project.show(vcd)


def fpga(N: Optional[str] = None):
    """Runs the FPGA implementation flow for the Heartbeat design.

    This flow targets a Xilinx Artix-7 FPGA (xc7a100tcsg324) and generates
    a bitstream that can be programmed onto the device.

    Args:
        N (str, optional): The value for the Verilog parameter 'N'.
            Defaults to None, which uses the value set in the design schema.
    """
    # Create a project instance for an FPGA flow.
    project = FPGA()

    # Instantiate and configure the design.
    hb = HeartbeatDesign()
    project.set_design(hb)

    # Add the RTL and FPGA constraint filesets.
    project.add_fileset("rtl")
    project.add_fileset("fpga.xc7a100tcsg324")
    # Specify the Xilinx implementation flow.
    project.set_flow(FPGAXilinxFlow())

    # Configure the specific FPGA part details.
    fpga = FPGADevice("xc7")
    fpga.set_partname("xc7a100tcsg324")
    project.set_fpga(fpga)

    # Optionally override the 'N' parameter.
    if N is not None:
        hb.set_param("N", N, fileset="rtl")

    # Run the FPGA flow (synthesis, place, route, bitstream generation).
    project.run()
    project.summary()


def sim_postpnr(pnr_jobname: Optional[str] = None,
                jobname: str = "sim", show_vcd: bool = True) -> str:
    """Runs a gate-level (post-PnR) simulation of the Heartbeat design.

    The implemented gate-level netlist is simulated against the Skywater130
    standard-cell Verilog models to capture a switching-activity waveform (VCD)
    that can later drive vector-based power analysis.

    If ``pnr_jobname`` is not provided, the ASIC implementation flow is run
    automatically (via :func:`asic`) under the job name ``"pnr"``; otherwise the
    netlist is reused from the named existing job.

    Args:
        pnr_jobname (str, optional): Job name of an existing ASIC implementation
            run to reuse. If None, :func:`asic` is run first.
        jobname (str): Job name for this simulation. Defaults to "sim".
        show_vcd (bool): If True, open the captured waveform in a viewer once the
            simulation completes. Defaults to True.

    Returns:
        str: The job name of the ASIC implementation whose netlist was simulated.
    """
    # Uniquify: registers the variant + wrapper filesets on `design`. The same
    # design is reused for hardening and gate sim so all filesets are in scope.
    design = HeartbeatDesign()
    uq = uniquify_heartbeat(design)

    # Ensure a hardened macro exists; harden the variants if a job was not
    # provided. build() runs each variant under jobname=<variant> for an isolated
    # build dir, and returns/persists the {variant: macro} it built.
    if pnr_jobname is None:
        def _target(project):
            project.add_fileset("sdc.skywater130")
            asic_target(project, pdk="skywater130")

        built = uq.build(target=_target)
        # heartbeat has a single parameterization, so one variant was built; its
        # name is the jobname of the implementation to simulate.
        (pnr_jobname,) = built
    else:
        uq.load_macros()
    macro = uq.macros[pnr_jobname]

    gate = design
    # Gate-level sim: the wrapper (restores the ``N`` parameter for the
    # testbench) plus the macro's 'rtl' fileset, which carries the hardened
    # netlist (module ``heartbeat__N8``) and, bundled as a recoverable
    # dependency, the standard-cell simulation models -- no PDK/impl lookup.
    with gate.active_fileset("netlist"):
        gate.add_depfileset(gate, depfileset="rtl.heartbeat.wrapper")
        gate.add_depfileset(macro, "rtl")

    sim = Sim(gate)
    # The regular parameterized testbench (heartbeat_tb) now drives the gate
    # netlist through the wrapper -- no dedicated heartbeat8_tb needed.
    sim.add_fileset(["testbench.icarus.v", "netlist"])
    sim.set_flow(DVFlow(tool="icarus"))
    sim.option.set_jobname(jobname)

    sim.run()
    sim.summary()

    vcd = sim.find_result(step="simulate", index="0", directory="reports",
                          filename="heartbeat_tb.vcd")

    # If a VCD file is found, open it with the default waveform viewer.
    if show_vcd and vcd:
        sim.show(vcd)

    return pnr_jobname


def power(pnr_jobname: Optional[str] = None, sim_jobname: Optional[str] = None):
    """Runs vector-based (VCD-driven) power signoff for the Heartbeat design.

    Chains three flows on the Skywater130 PDK to obtain a power estimate driven
    by real switching activity rather than default toggle rates:

        1. **asicflow** (:func:`asic`): RTL-to-GDS implementation, producing a
           gate-level netlist and extracted parasitics (SPEF).
        2. **dvflow** (:func:`sim_postpnr`): gate-level simulation of the
           netlist, capturing a switching-activity waveform (VCD).
        3. **timing signoff**: OpenSTA reads the netlist and SDC from the design
           filesets, the SPEF from the staged step inputs and the VCD (via
           ``read_vcd``), and reports vector-based power.

    Any prerequisite job that is not supplied is run automatically: if
    ``sim_jobname`` is None the simulation (and, if needed, the implementation)
    is run; if only ``pnr_jobname`` is None the implementation is run.

    Gate-level simulation is demonstrated with Skywater130 because it is the demo
    PDK that ships behavioral Verilog cell models (FreePDK45/Nangate45 does not).

    Args:
        pnr_jobname (str, optional): Job name of an existing ASIC implementation
            run to reuse.
        sim_jobname (str, optional): Job name of an existing gate-level
            simulation to reuse.
    """
    # Ensure the simulation (and, transitively, the implementation) exist.
    if sim_jobname is None:
        sim_jobname = "sim"
        pnr_jobname = sim_postpnr(pnr_jobname=pnr_jobname, jobname=sim_jobname, show_vcd=False)
    elif pnr_jobname is None:
        # Reusing an existing simulation: the netlist and parasitics must come
        # from the matching implementation, so require it explicitly rather than
        # silently pairing the VCD with the default "pnr" job.
        raise ValueError(
            "pnr_jobname is required when reusing an existing sim_jobname")

    # The hardened macro carries the structural netlist and SDC filesets we need
    # for signoff; recover the uniquify handle (regenerating is cheap and
    # deterministic) and load the persisted macro. heartbeat has a single
    # parameterization, hence one variant.
    uq = uniquify_heartbeat()
    (variant_name,) = uq.variant_names
    uq.load_macros()
    macro = uq.macros[variant_name]

    # SPEF (extracted parasitics) is not part of the macro; get it from the
    # implementation run (located under uniquify's libdir).
    impl = ASIC.from_manifest(filepath=uq.manifest(pnr_jobname))
    spef = impl.find_result("typical.spef", step="write.views")

    # Load the simulation manifest to locate the captured waveform.
    sim = Sim.from_manifest(
        filepath=f"build/heartbeat/{sim_jobname}/heartbeat.pkg.json")
    vcd = sim.find_result(step="simulate", index="0", directory="reports",
                          filename="heartbeat_tb.vcd")

    # ------------------------------------------------------------------
    # Timing signoff: netlist + SDC (macro filesets) + SPEF (inputs) + VCD -> power
    # ------------------------------------------------------------------
    signoff = ASIC()
    # The macro is self-contained and already provides the 'netlist' (structural,
    # for STA) and 'sdc' filesets, so use it as the signoff design directly
    # instead of rebuilding them. Register the captured VCD in its own fileset but
    # do NOT make it active: it requires a scope, so it is consumed only via the
    # scoped power-activity configuration below.
    macro.add_file(vcd, fileset="sim.vcd", filetype="vcd")
    signoff.set_design(macro)
    signoff.add_fileset(["netlist", "sdc"])

    # Reuse the Skywater130 target for the standard-cell Liberty, corners and
    # delay model (STA resolves the netlist's cells from these); its flow is
    # replaced with the timing-signoff flow below.
    skywater130_demo(signoff)

    signoff_flow = Flowgraph("timingsignoff")
    # Stage the parasitics into the timing node's inputs; sc_timing.tcl reads
    # the per-corner SPEF from the step inputs (there is no SPEF fileset type).
    signoff_flow.node("stage", ImportFilesTask())
    signoff_flow.node("signoff", TimingTask())
    signoff_flow.edge("stage", "signoff")
    signoff.set_flow(signoff_flow)
    signoff.option.set_jobname("timingsignoff")

    ImportFilesTask.find_task(signoff).add_import_file(spef)

    # Annotate switching activity from the VCD. The testbench instantiates the
    # wrapper as heartbeat_tb/DUT, and the wrapper forwards to the hardened
    # variant in its generate block; uniquify knows that internal path, so the
    # netlist (signoff top) lives at heartbeat_tb/DUT/g_<variant>/<instance>.
    scope = uq.instance_path(variant_name, parent="heartbeat_tb/DUT")
    TimingTask.find_task(signoff).add_opensta_poweractivity(
        scope, macro.name, "sim.vcd")

    signoff.run()
    signoff.summary()


def check():
    """Checks that all file paths in the HeartbeatDesign are valid.

    This is a simple utility function to ensure that all source files
    referenced in the design schema actually exist.
    """
    assert HeartbeatDesign().check_filepaths()


def screenshot(gds: str = "build/heartbeat/job0/write.gds/0/outputs/heartbeat.gds.gz"):
    """Generates a high-resolution screenshot of the Heartbeat design layout.

    This function runs a specialized flow that imports the final GDSII layout,
    prepares it for visualization, takes tiled screenshots, and merges them
    into a single high-resolution image.
    """
    # Create a project instance for an ASIC flow.
    project = ASIC()

    # Instantiate and configure the design.
    hb = HeartbeatDesign()
    project.set_design(hb)

    project.add_fileset("rtl")

    # Load the target configuration for FreePDK45.
    asic_target(project, pdk="freepdk45")

    # Specify the high-resolution screenshot flow.
    project.set_flow(HighResScreenshotFlow(add_prepare=False))

    # Import the specified GDS file.
    ImportFilesTask.find_task(project).add_import_file(gds)

    # Configure KLayout screenshot parameters.
    screenshot_task = ScreenshotTask.find_task(project)
    screenshot_task.set_klayout_bins(2, 2)

    project.option.set_jobname("screenshot")
    project.option.set_nodashboard(True)

    # Run the screenshot flow.
    project.run()


if __name__ == "__main__":
    # When the script is executed directly from the command line,
    # run the synthesis flow by default.
    syn()
