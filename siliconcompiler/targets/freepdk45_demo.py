# Import necessary classes from the siliconcompiler framework and the LambdaPDK.
from siliconcompiler import ASIC
from siliconcompiler.flows import asicflow, synflow

from lambdapdk.freepdk45.libs.nangate45 import Nangate45
from lambdapdk.freepdk45.libs.fakeram45 import FakeRAM45Lambdalib_SinglePort


####################################################
# Target Setup Function
####################################################
def freepdk45_demo(
        project: ASIC,
        syn_np: int = 1,
        floorplan_np: int = 1, place_np: int = 1, cts_np: int = 1, route_np: int = 1,
        timing_np: int = 1):
    """
        Configure an ASIC for the FreePDK45 process: load Nangate45 standard-cell library,
        set synthesis/implementation flows, select the PDK, apply a typical timing scenario and
        NLDM delay model, set area constraints, and alias the fake RAM library.

        Parameters:
            * project (ASIC): Project to configure.
            * syn_np (int): Parallelism (number of worker processes) for synthesis.
            * floorplan_np (int): Parallelism for floorplanning.
            * place_np (int): Parallelism for placement.
            * cts_np (int): Parallelism for clock-tree synthesis.
            * route_np (int): Parallelism for routing.
            * timing_np (int): Parallelism for timing analysis.
        """

    # 1. Load Standard Cell Library
    # Sets the Nangate45 open-source standard cell library as the primary
    # library for the design.
    project.set_mainlib(Nangate45())

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
    project.set_pdk("freepdk45")

    # 4. Define Timing Constraints
    # For this demonstration target, a single "typical" timing corner is
    # configured to check for both setup and hold violations. In a real
    # production flow, separate slow and fast corners would be used.
    scenario = project.constraint.timing.make_scenario("typical")
    scenario.add_libcorner(["typical", "generic"])
    scenario.set_pexcorner("typical")
    scenario.add_check(["setup", "hold"])

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
    # Makes the fake SRAM library available to the flow under a common,
    # standardized naming convention.
    FakeRAM45Lambdalib_SinglePort.alias(project)
