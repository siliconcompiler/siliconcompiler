# Import necessary classes from the siliconcompiler framework and the LambdaPDK.
from siliconcompiler import ASIC
from siliconcompiler.flows import asicflow, synflow

from lambdapdk.ihp130.libs.sg13g2_stdcell import IHP130StdCell_1p2
from lambdapdk.ihp130.libs.sg13g2_sram import IHP130Lambdalib_SinglePort
from lambdapdk.ihp130.libs.sg13g2_io import IHP130LambdaLib_IO_1p2


####################################################
# Target Setup Function
####################################################
def ihp130_demo(
        project: ASIC,
        syn_np: int = 1,
        floorplan_np: int = 1, place_np: int = 1, cts_np: int = 1, route_np: int = 1,
        timing_np: int = 1):
    """
        Configure a siliconcompiler ASIC for the IHP 130nm PDK, including libraries,
        flows, timing scenarios, and basic physical constraints.

        Sets the project's main standard-cell library, configures full ASIC and synthesis-only
        flows with provided parallelism, selects the "ihp130" PDK, creates slow/typical/fast STA
        scenarios, sets the ASIC delay model to "nldm", applies core area density and margin
        constraints, and registers the IHP130 SRAM and IO libraries.

        Parameters:
            * project (ASIC): The siliconcompiler project to configure.
            * syn_np (int): Parallelism for synthesis-related steps.
            * floorplan_np (int): Parallelism for floorplanning.
            * place_np (int): Parallelism for placement.
            * cts_np (int): Parallelism for clock-tree synthesis.
            * route_np (int): Parallelism for routing.
            * timing_np (int): Parallelism for timing analysis (synthesis-only flow).
        """

    # 1. Load Standard Cell Library
    # Sets the primary standard cell library for the design. This library
    # contains the basic building blocks (gates, flip-flops) for synthesis.
    project.set_mainlib(IHP130StdCell_1p2())

    # 2. Configure Compilation Flows
    # Defines the sequence of steps (tools) for the complete ASIC design flow
    # from synthesis to GDSII. Also adds a separate synthesis-only flow.
    project.set_flow(asicflow.ASICFlow(
        syn_np=syn_np,
        floorplan_np=floorplan_np,
        place_np=place_np,
        cts_np=cts_np,
        route_np=route_np))
    project.add_dep(synflow.SynthesisFlow(
        syn_np=syn_np,
        timing_np=timing_np))

    # 3. Set Target PDK
    # Specifies the process development kit to be used.
    project.set_pdk("ihp130")

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
    # Set a margin of 4.8 microns around the core area.
    area.set_coremargin(4.8)

    # 6. Alias and Register IP/Macro Libraries
    # Makes specialized libraries like SRAM and IO cells available to the flow
    # under a common, standardized naming convention.
    IHP130Lambdalib_SinglePort.alias(project)
    IHP130LambdaLib_IO_1p2.alias(project)
