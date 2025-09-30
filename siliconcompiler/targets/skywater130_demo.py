# Import necessary classes from the siliconcompiler framework and the LambdaPDK.
from siliconcompiler import ASIC

from siliconcompiler.flows import asicflow, synflow

from lambdapdk.sky130.libs.sky130sc import Sky130_SCHDLibrary
from lambdapdk.sky130.libs.sky130sram import Sky130Lambdalib_SinglePort
from lambdapdk.sky130.libs.sky130io import Sky130LambdaLib_IO


####################################################
# Target Setup Function
####################################################
def skywater130_demo(
        project: ASIC,
        syn_np: int = 1,
        floorplan_np: int = 1, place_np: int = 1, cts_np: int = 1, route_np: int = 1,
        timing_np: int = 1):
    '''
    Configures a siliconcompiler project for the Skywater130 process development kit (PDK).

    This function sets up the entire compilation pipeline, including the
    standard cell library, compilation flows, timing constraints, and
    physical design parameters for a Skywater130 target.

    Args:
        * project (:class:`ASIC`): The siliconcompiler project to configure.
        * syn_np (int): Number of parallel processes for synthesis.
        * floorplan_np (int): Number of parallel processes for floorplanning.
        * place_np (int): Number of parallel processes for placement.
        * cts_np (int): Number of parallel processes for clock tree synthesis.
        * route_np (int): Number of parallel processes for routing.
        * timing_np (int): Number of parallel processes for timing analysis.
    '''

    # 1. Load Standard Cell Library
    # Sets the primary standard cell library for the design. This library
    # contains the basic building blocks (gates, flip-flops) for synthesis.
    project.set_mainlib(Sky130_SCHDLibrary())

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
    project.set_pdk("skywater130")

    # 4. Define Timing Corners for Static Timing Analysis (STA)
    # Sets up different scenarios to analyze timing performance under various
    # process, voltage, and temperature (PVT) conditions.

    # Slow corner: Checks for setup time violations at worst-case conditions.
    scenario = project.constraint.timing.make_scenario("slow")
    scenario.add_libcorner(["slow", "generic"])
    scenario.set_pexcorner("typical")
    scenario.add_check("setup")

    # Typical corner: Used for power analysis under nominal conditions.
    scenario = project.constraint.timing.make_scenario("typical")
    scenario.add_libcorner(["typical", "generic"])
    scenario.set_pexcorner("typical")
    scenario.add_check("power")

    # Fast corner: Checks for hold time violations at best-case conditions.
    scenario = project.constraint.timing.make_scenario("fast")
    scenario.add_libcorner(["fast", "generic"])
    scenario.set_pexcorner("typical")
    scenario.add_check("hold")

    # Set the delay model used for timing calculations. NLDM is a common standard.
    project.set_asic_delaymodel("nldm")

    # 5. Define Physical Design Constraints
    # These constraints guide the place-and-route tools.
    area = project.constraint.area
    # Target a core utilization of 40%.
    area.set_density(40)
    # Set a margin of 1 micron around the core area.
    area.set_coremargin(1)

    # 6. Alias and Register IP/Macro Libraries
    # Makes specialized libraries like SRAM and IO cells available to the flow
    # under a common, standardized naming convention.
    Sky130Lambdalib_SinglePort.alias(project)
    Sky130LambdaLib_IO.alias(project)
