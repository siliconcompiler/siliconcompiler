# Import necessary classes from the siliconcompiler framework and the LambdaPDK.
from siliconcompiler import ASIC
from siliconcompiler.flows import asicflow, synflow

from lambdapdk.asap7.libs.asap7sc7p5t import ASAP7SC7p5RVT, ASAP7SC7p5SLVT, ASAP7SC7p5LVT
from lambdapdk.asap7.libs.fakeram7 import FakeRAM7Lambdalib_SinglePort, \
    FakeRAM7Lambdalib_DoublePort, \
    FakeRAM7Lambdalib_TrueDoublePort
from lambdapdk.asap7.libs.fakeio7 import FakeIO7Lambdalib_IO


####################################################
# Target Setup Function
####################################################
def asap7_demo(
        project: ASIC,
        syn_np: int = 1,
        floorplan_np: int = 1, place_np: int = 1, cts_np: int = 1, route_np: int = 1,
        timing_np: int = 1):
    """
        Configure an ASIC for the ASAP7 PDK with multi-Vt libraries, flows, timing corners,
        and physical constraints.

        Sets the main and additional standard-cell libraries (RVT, LVT, SLVT), installs synthesis
        and full ASIC flows, selects the "asap7" PDK, creates slow/typical/fast STA scenarios
        using NLDM delay model, applies area constraints (40% core density, 1 µm core margin),
        and registers example IP/macro library aliases.

        Parameters:
            * project (ASIC): The siliconcompiler project to configure.
            * syn_np (int): Parallel process count for synthesis.
            * floorplan_np (int): Parallel process count for floorplanning.
            * place_np (int): Parallel process count for placement.
            * cts_np (int): Parallel process count for clock-tree synthesis.
            * route_np (int): Parallel process count for routing.
            * timing_np (int): Parallel process count for timing-analysis synthesis.
        """

    # 1. Load Standard Cell Libraries
    # ASAP7 provides cells with different threshold voltages (Vt) to allow for
    # trade-offs between performance and power consumption.
    # RVT (Regular Vt) is set as the default main library.
    # LVT (Low Vt) and SLVT (Super Low Vt) are also added for the tools to use
    # for timing optimization on critical paths.
    project.set_mainlib(ASAP7SC7p5RVT())
    project.add_asiclib(ASAP7SC7p5LVT())
    project.add_asiclib(ASAP7SC7p5SLVT())

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
    # Specifies the process development kit to be used, which contains
    # technology-specific information for the ASAP7 process.
    project.set_pdk("asap7")

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
    # under a common, standardized naming convention. These are 'fake' libraries
    # for demonstration and academic purposes.
    FakeRAM7Lambdalib_SinglePort.alias(project)
    FakeRAM7Lambdalib_DoublePort.alias(project)
    FakeRAM7Lambdalib_TrueDoublePort.alias(project)
    FakeIO7Lambdalib_IO.alias(project)
