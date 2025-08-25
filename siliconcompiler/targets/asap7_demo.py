from siliconcompiler import ASICProject
from siliconcompiler.flows import asicflow, synflow

from lambdapdk.asap7.libs.asap7sc7p5t import ASAP7SC7p5RVT, ASAP7SC7p5SLVT, ASAP7SC7p5LVT
from lambdapdk.asap7.libs.fakeram7 import FakeRAM7Lambdalib_SinglePort, FakeRAM7Lambdalib_DoublePort


####################################################
# Target Setup
####################################################
def setup(project: ASICProject, syn_np=1, floorplan_np=1, physyn_np=1, place_np=1, cts_np=1,
          route_np=1,
          timing_np=1):
    '''
    ASAP7 Demo Target
    '''

    # 1. Load Libraries
    project.set_mainlib(ASAP7SC7p5RVT())
    project.add_asiclib(ASAP7SC7p5LVT())
    project.add_asiclib(ASAP7SC7p5SLVT())

    # 2. Load flows
    project.set_flow(asicflow.ASICFlow())
    project.add_dep(synflow.SynthesisFlowgraph())

    # 3. Set default targets
    project.set_pdk("asap7")

    # 4. Timing corners
    scenario = project.get_timingconstraints().make_scenario("slow")
    scenario.add_libcorner("slow")
    scenario.set_pexcorner("typical")
    scenario.add_check("setup")
    scenario = project.get_timingconstraints().make_scenario("typical")
    scenario.add_libcorner("typical")
    scenario.set_pexcorner("typical")
    scenario.add_check("power")
    scenario = project.get_timingconstraints().make_scenario("fast")
    scenario.add_libcorner("fast")
    scenario.set_pexcorner("typical")
    scenario.add_check("hold")

    project.set_asic_delaymodel("nldm")

    # 5. Physical constraints
    area = project.get_areaconstraints()
    area.set_density(40)
    area.set_coremargin(1)

    # 5. Assign Lambdalib aliases
    FakeRAM7Lambdalib_SinglePort.alias(project)
    FakeRAM7Lambdalib_DoublePort.alias(project)
