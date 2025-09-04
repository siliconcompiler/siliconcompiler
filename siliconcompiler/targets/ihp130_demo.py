from siliconcompiler import ASICProject
from siliconcompiler.flows import asicflow, synflow

from lambdapdk.ihp130.libs.sg13g2_stdcell import IHP130StdCell_1p2
from lambdapdk.ihp130.libs.sg13g2_sram import IHP130Lambdalib_SinglePort


####################################################
# Target Setup
####################################################
def setup(project: ASICProject, syn_np=1, floorplan_np=1, physyn_np=1, place_np=1, cts_np=1,
          route_np=1,
          timing_np=1):
    '''
    IHP130 Demo Target
    '''

    # 1. Load Libraries
    project.set_mainlib(IHP130StdCell_1p2())

    # 2. Load flows
    project.set_flow(asicflow.ASICFlow())
    project.add_dep(synflow.SynthesisFlow())

    # 3. Set default targets
    project.set_pdk("ihp130")

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
    area.set_coremargin(4.8)

    # 5. Assign Lambdalib aliases
    IHP130Lambdalib_SinglePort.alias(project)
