from siliconcompiler import ASICProject

from siliconcompiler.flows import asicflow, synflow

from lambdapdk.sky130.libs.sky130sc import Sky130_SCHDLibrary
from lambdapdk.sky130.libs.sky130sram import Sky130Lambdalib_SinglePort
from lambdapdk.sky130.libs.sky130io import Sky130LambdaLib_IO


####################################################
# Target Setup
####################################################
def setup(project: ASICProject, syn_np=1, floorplan_np=1, physyn_np=1, place_np=1, cts_np=1,
          route_np=1,
          timing_np=1):
    """
          Configure a SkyWater 130 target and standard design constraints on an ASICProject.
          
          Sets the project's main library and flows, selects the "skywater130" PDK, creates three timing scenarios ("slow", "typical", "fast") with associated library corners, PEX corners and checks, sets the ASIC delay model to "nldm", configures physical area constraints (density and core margin), and registers Sky130 lambda library aliases with the project.
          
          Parameters:
              project (ASICProject): The ASICProject to configure.
              syn_np (int): Parallelism for synthesis-related tasks (unused directly here but accepted for caller convenience).
              floorplan_np (int): Parallelism for floorplanning tasks.
              physyn_np (int): Parallelism for physical synthesis tasks.
              place_np (int): Parallelism for placement tasks.
              cts_np (int): Parallelism for clock-tree synthesis tasks.
              route_np (int): Parallelism for routing tasks.
              timing_np (int): Parallelism for timing analysis tasks.
          """

    # 1. Load Libraries
    project.set_mainlib(Sky130_SCHDLibrary())

    # 2. Load flows
    project.set_flow(asicflow.ASICFlow())
    project.add_dep(synflow.SynthesisFlow())

    # 3. Set default targets
    project.set_pdk("skywater130")

    # 4. Timing corners
    scenario = project.constraint.timing.make_scenario("slow")
    scenario.add_libcorner(["slow", "generic"])
    scenario.set_pexcorner("typical")
    scenario.add_check("setup")
    scenario = project.constraint.timing.make_scenario("typical")
    scenario.add_libcorner(["typical", "generic"])
    scenario.set_pexcorner("typical")
    scenario.add_check("power")
    scenario = project.constraint.timing.make_scenario("fast")
    scenario.add_libcorner(["fast", "generic"])
    scenario.set_pexcorner("typical")
    scenario.add_check("hold")

    project.set_asic_delaymodel("nldm")

    # 5. Physical constraints
    area = project.constraint.area
    area.set_density(40)
    area.set_coremargin(1)

    # 5. Assign Lambdalib aliases
    Sky130Lambdalib_SinglePort.alias(project)
    Sky130LambdaLib_IO.alias(project)
