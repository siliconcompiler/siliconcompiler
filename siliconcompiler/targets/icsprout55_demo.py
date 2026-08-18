# Import necessary classes from the siliconcompiler framework and the LambdaPDK.
from typing import Optional

from siliconcompiler import ASIC
from siliconcompiler.flows import asicflow, synflow

from siliconcompiler.targets._utils import detect_elaboration_language

from lambdapdk.icsprout55.libs.stdcells import ICS55StdCellRVT, ICS55StdCellHVT, ICS55StdCellLVT


####################################################
# Target Setup Function
####################################################
def icsprout55_demo(
        project: ASIC,
        syn_np: int = 1,
        floorplan_np: int = 1, place_np: int = 1, cts_np: int = 1, route_np: int = 1,
        timing_np: int = 1,
        language: Optional[str] = None):
    """
        Configure a siliconcompiler ASIC for the ICsprout 55nm PDK.

        Sets the project's main standard-cell library, configures full ASIC and synthesis-only
        flows with provided parallelism, selects the "icsprout55" PDK, creates slow/typical/fast
        STA scenarios, sets the ASIC delay model to "nldm", and applies core area density and
        margin constraints.

        Parameters:
            * project (ASIC): The siliconcompiler project to configure.
            * syn_np (int): Parallelism for synthesis-related steps.
            * floorplan_np (int): Parallelism for floorplanning.
            * place_np (int): Parallelism for placement.
            * cts_np (int): Parallelism for clock-tree synthesis.
            * route_np (int): Parallelism for routing.
            * timing_np (int): Parallelism for timing analysis (synthesis-only flow).
            * language (str): Elaboration language, detected from the design if not given.
        """
    if language is None:
        language = detect_elaboration_language(project)

    # 1. Load Standard Cell Library
    # Sets the primary standard cell library for the design. This library
    # contains the basic building blocks (gates, flip-flops) for synthesis.
    # The three Vt flavors ship the same 747 cells; the regular Vt library is the
    # default. The Verilog models of the three declare the same UDP primitive names,
    # so a multi-Vt netlist cannot be compiled for gate-level simulation.
    project.set_mainlib(ICS55StdCellRVT())
    project.add_asiclib(ICS55StdCellRVT())
    project.add_asiclib(ICS55StdCellHVT())
    project.add_asiclib(ICS55StdCellLVT())

    # 2. Configure Compilation Flows
    # Defines the sequence of steps (tools) for the complete ASIC design flow
    # from synthesis to GDSII. Also adds a separate synthesis-only flow.
    project.set_flow(asicflow.ASICFlow(
        syn_np=syn_np,
        floorplan_np=floorplan_np,
        place_np=place_np,
        cts_np=cts_np,
        route_np=route_np,
        language=language))
    project.add_dep(synflow.SynthesisFlow(
        syn_np=syn_np,
        timing_np=timing_np,
        language=language))

    # 3. Set Target PDK
    # Specifies the process development kit to be used.
    project.set_pdk("icsprout55")

    # 4. Define Timing Corners for Static Timing Analysis (STA)
    # Sets up different scenarios to analyze timing performance under various
    # process, voltage, and temperature (PVT) conditions.

    # Slow corner: Checks for setup time violations at worst-case conditions.
    scenario = project.constraint.timing.make_scenario("slow")
    scenario.add_libcorner("slow")
    scenario.set_pexcorner("typical")
    scenario.add_check("setup")

    # Typical corner: Used for power analysis under nominal conditions.
    scenario = project.constraint.timing.make_scenario("typical")
    scenario.add_libcorner("typical")
    scenario.set_pexcorner("typical")
    scenario.add_check("power")

    # Fast corner: Checks for hold time violations at best-case conditions.
    scenario = project.constraint.timing.make_scenario("fast")
    scenario.add_libcorner("fast")
    scenario.set_pexcorner("typical")
    scenario.add_check("hold")

    # Set the delay model used for timing calculations. NLDM is a common standard.
    project.set_asic_delaymodel("nldm")

    # 5. Define Physical Design Constraints
    # These constraints guide the place-and-route tools.
    area = project.constraint.area
    # Target a core utilization of 40%.
    area.set_density(40)
    # Set a margin of 1.0 microns around the core area.
    area.set_coremargin(1.0)
