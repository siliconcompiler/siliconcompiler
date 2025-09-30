# Import necessary classes from the siliconcompiler framework and the LambdaPDK.
from siliconcompiler import ASIC
from siliconcompiler.flows import asicflow, synflow

from lambdapdk.gf180 import GF180_5LM_1TM_9K_9t
from lambdapdk.gf180.libs.gf180mcu import GF180_MCU_9T_5LMLibrary
from lambdapdk.gf180.libs.gf180sram import GF180Lambdalib_SinglePort
from lambdapdk.gf180.libs.gf180io import GF180Lambdalib_IO_5LM


####################################################
# Target Setup Function
####################################################
def gf180_demo(
        project: ASIC,
        syn_np: int = 1,
        floorplan_np: int = 1, place_np: int = 1, cts_np: int = 1, route_np: int = 1,
        timing_np: int = 1):
    """
        Configure an ASIC for the GlobalFoundries 180nm (GF180) process by registering
        the PDK and standard-cell/IP libraries, installing compilation flows, creating STA
        timing corners, and setting physical area constraints.

        Parameters:
            * project (ASIC): The siliconcompiler project to configure.
            * syn_np (int): Parallelism for synthesis.
            * floorplan_np (int): Parallelism for floorplanning.
            * place_np (int): Parallelism for placement.
            * cts_np (int): Parallelism for clock-tree synthesis.
            * route_np (int): Parallelism for routing.
            * timing_np (int): Parallelism for timing analysis.
        """

    # 1. Load PDK and Standard Cell Libraries
    # Sets the process development kit and the standard cell libraries
    # that provide the basic logic gates and flip-flops for the design.
    project.set_pdk(GF180_5LM_1TM_9K_9t())
    project.add_asiclib(GF180_MCU_9T_5LMLibrary())
    project.set_mainlib(GF180_MCU_9T_5LMLibrary())

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

    # 3. Define Timing Corners for Static Timing Analysis (STA)
    # Sets up different scenarios to analyze timing performance under various
    # process, voltage, and temperature (PVT) conditions. Note the specific
    # voltages set for each corner.

    # Slow corner: Checks for setup time violations at worst-case conditions
    # (slow process, low voltage).
    scenario = project.constraint.timing.make_scenario("slow")
    scenario.add_libcorner("slow")
    scenario.set_pexcorner("wst")
    scenario.add_check("setup")
    scenario.set_pin_voltage("VDD", 4.5)

    # Typical corner: Used for power analysis under nominal conditions.
    scenario = project.constraint.timing.make_scenario("typical")
    scenario.add_libcorner("typical")
    scenario.set_pexcorner("typ")
    scenario.add_check("power")
    scenario.set_pin_voltage("VDD", 5.0)

    # Fast corner: Checks for hold time violations at best-case conditions
    # (fast process, high voltage).
    scenario = project.constraint.timing.make_scenario("fast")
    scenario.add_libcorner("fast")
    scenario.set_pexcorner("bst")
    scenario.add_check("hold")
    scenario.set_pin_voltage("VDD", 5.5)

    # Set the delay model used for timing calculations. NLDM is a common standard.
    project.set_asic_delaymodel("nldm")

    # 4. Define Physical Design Constraints
    # These constraints guide the place-and-route tools.
    area = project.constraint.area
    # Target a core utilization of 40%.
    area.set_density(40)
    # Set a margin of 1 micron around the core area.
    area.set_coremargin(1)

    # 5. Alias and Register IP/Macro Libraries
    # Makes specialized libraries like SRAM and IO cells available to the flow
    # under a common, standardized naming convention.
    GF180Lambdalib_SinglePort.alias(project)
    GF180Lambdalib_IO_5LM.alias(project)
