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
    '''
    FreePDK45 demo target
    '''

    # 1. Load Libraries
    project.set_mainlib(Nangate45())

    # 2. Load flows
    project.set_flow(asicflow.ASICFlow())
    project.add_dep(synflow.SynthesisFlowgraph())

    # 3. Set default targets
    project.set_pdk("freepdk45")

    # 4. Timing corners
    scenario = project.get_timingconstraints().make_scenario("typical")
    scenario.add_libcorner("typical")
    scenario.set_pexcorner("typical")
    scenario.add_check(["setup", "hold"])

    project.set_asic_delaymodel("nldm")

    # 5. Physical constraints
    area = project.get_areaconstraints()
    area.set_density(40)
    area.set_coremargin(1)

    # 5. Assign Lambdalib aliases
    FakeRAM45Lambdalib_SinglePort.alias(project)
