# Import necessary classes from the siliconcompiler framework and the LambdaPDK.
from typing import Optional

from siliconcompiler import ASIC
from siliconcompiler.flows import asicflow, synflow

from siliconcompiler.targets._utils import detect_elaboration_language

from lambdapdk.gt2n.libs.stdcells import GT2N6TW31LVT, GT2N6TW31HVT, GT2N6TW31SVT, GT2N6TW31ULVT, \
    GT2N6TW31ELVT


####################################################
# Target Setup Function
####################################################
def gt2n_demo(
        project: ASIC,
        syn_np: int = 1,
        floorplan_np: int = 1, place_np: int = 1, cts_np: int = 1, route_np: int = 1,
        timing_np: int = 1,
        language: Optional[str] = None):
    """
        Configure a siliconcompiler ASIC for the GT2N.

        Sets the project's main standard-cell library, configures full ASIC and synthesis-only
        flows with provided parallelism, selects the "gt2n" PDK, creates slow/typical/fast STA
        scenarios, sets the ASIC delay model to "nldm", applies core area density and margin
        constraints.

        Parameters:
            * project (ASIC): The siliconcompiler project to configure.
            * syn_np (int): Parallelism for synthesis-related steps.
            * floorplan_np (int): Parallelism for floorplanning.
            * place_np (int): Parallelism for placement.
            * cts_np (int): Parallelism for clock-tree synthesis.
            * route_np (int): Parallelism for routing.
            * timing_np (int): Parallelism for timing analysis (synthesis-only flow).
        """
    if language is None:
        language = detect_elaboration_language(project)

    # 1. Load Standard Cell Library
    # Sets the primary standard cell library for the design. This library
    # contains the basic building blocks (gates, flip-flops) for synthesis.
    main = GT2N6TW31SVT()
    project.set_mainlib(main)
    for lib in [main, GT2N6TW31HVT(), GT2N6TW31LVT(), GT2N6TW31ULVT(), GT2N6TW31ELVT()]:
        project.add_asiclib(lib)

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
    project.set_pdk("gt2n")

    # 4. Define Timing Corners for Static Timing Analysis (STA)
    # Sets up different scenarios to analyze timing performance under various
    # process, voltage, and temperature (PVT) conditions.

    # Typical corner: Used for power analysis under nominal conditions.
    scenario = project.constraint.timing.make_scenario("typical")
    scenario.add_libcorner("typical")
    scenario.set_pexcorner("typical")
    scenario.add_check(["setup", "hold", "power"])

    # Set the delay model used for timing calculations. NLDM is a common standard.
    project.set_asic_delaymodel("nldm")

    # 5. Define Physical Design Constraints
    # These constraints guide the place-and-route tools.
    area = project.constraint.area
    # Target a core utilization of 40%.
    area.set_density(40)
    # Set a margin of 1.0 microns around the core area.
    area.set_coremargin(1.0)
