from siliconcompiler import ASICProject

from siliconcompiler.flows import asicflow, synflow

from lambdapdk.sky130.libs.sky130sc import Sky130_SCHDLibrary
from lambdapdk.sky130.libs.sky130sram import Sky130Lambdalib_SinglePort


####################################################
# Target Setup
####################################################
def setup(project: ASICProject, syn_np=1, floorplan_np=1, physyn_np=1, place_np=1, cts_np=1,
          route_np=1,
          timing_np=1):
    '''
    Skywater130 Demo Target
    '''

    # 1. Load Libraries
    project.set_mainlib(Sky130_SCHDLibrary())

    # 2. Load flows
    project.set_flow(asicflow.ASICFlow())
    project.add_dep(synflow.SynthesisFlowgraph())

    # 3. Set default targets
    project.set_pdk("skywater130")

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
    Sky130Lambdalib_SinglePort.alias(project)
