from siliconcompiler import ASICProject
from siliconcompiler.flows import asicflow, synflow

from lambdapdk.freepdk45.libs.nangate45 import Nangate45
from lambdapdk.freepdk45.libs.fakeram45 import FakeRAM45Lambdalib_SinglePort


####################################################
# Target Setup
####################################################
def setup(project: ASICProject, syn_np=1, floorplan_np=1, physyn_np=1, place_np=1, cts_np=1,
          route_np=1,
          timing_np=1):
    """
          Configure an ASICProject instance for a FreePDK45 demo target.
          
          Sets the project's main library to Nangate45, configures the primary and dependent flows,
          selects the "freepdk45" PDK, creates a "typical" timing scenario with library corners
          and setup/hold checks, sets the ASIC delay model to "nldm", applies area constraints
          (routing density and core margin), and registers the FakeRAM45 single-port lambdalib alias.
          
          Parameters:
              project (ASICProject): The project to configure.
              syn_np (int): Parallelism (number of processes/threads) intended for synthesis.
              floorplan_np (int): Parallelism intended for floorplanning.
              physyn_np (int): Parallelism intended for physical synthesis.
              place_np (int): Parallelism intended for placement.
              cts_np (int): Parallelism intended for clock-tree synthesis.
              route_np (int): Parallelism intended for routing.
              timing_np (int): Parallelism intended for timing analysis.
          """

    # 1. Load Libraries
    project.set_mainlib(Nangate45())

    # 2. Load flows
    project.set_flow(asicflow.ASICFlow())
    project.add_dep(synflow.SynthesisFlow())

    # 3. Set default targets
    project.set_pdk("freepdk45")

    # 4. Timing corners
    scenario = project.constraint.timing.make_scenario("typical")
    scenario.add_libcorner(["typical", "generic"])
    scenario.set_pexcorner("typical")
    scenario.add_check(["setup", "hold"])

    project.set_asic_delaymodel("nldm")

    # 5. Physical constraints
    area = project.constraint.area
    area.set_density(40)
    area.set_coremargin(1)

    # 5. Assign Lambdalib aliases
    FakeRAM45Lambdalib_SinglePort.alias(project)
