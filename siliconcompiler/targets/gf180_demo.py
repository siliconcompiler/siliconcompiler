from siliconcompiler import ASICProject
from siliconcompiler.flows import asicflow, synflow

from lambdapdk.gf180 import GF180_5LM_1TM_9K_9t
from lambdapdk.gf180.libs.gf180mcu import GF180_MCU_9T_5LMLibrary
from lambdapdk.gf180.libs.gf180sram import GF180Lambdalib_SinglePort


####################################################
# Target Setup
####################################################
def setup(project: ASICProject, syn_np=1, floorplan_np=1, physyn_np=1, place_np=1, cts_np=1,
          route_np=1,
          timing_np=1):
    '''
    Global foundries 180 Demo Target
    '''

    # 1. Load PDK and Libraries
    project.set_pdk(GF180_5LM_1TM_9K_9t())
    project.add_asiclib(GF180_MCU_9T_5LMLibrary())
    project.set_mainlib(GF180_MCU_9T_5LMLibrary())

    # 2. Load flows
    project.set_flow(asicflow.ASICFlow())
    project.add_dep(synflow.SynthesisFlow())

    # 3. Set default targets

    # 4. Timing corners
    scenario = project.get_timingconstraints().make_scenario("slow")
    scenario.add_libcorner("slow")
    scenario.set_pexcorner("wst")
    scenario.add_check("setup")
    scenario.set_pin_voltage("VDD", 4.5)
    scenario = project.get_timingconstraints().make_scenario("typical")
    scenario.add_libcorner("typical")
    scenario.set_pexcorner("typ")
    scenario.add_check("power")
    scenario.set_pin_voltage("VDD", 5.0)
    scenario = project.get_timingconstraints().make_scenario("fast")
    scenario.add_libcorner("fast")
    scenario.set_pexcorner("bst")
    scenario.add_check("hold")
    scenario.set_pin_voltage("VDD", 5.5)

    project.set_asic_delaymodel("nldm")

    # 5. Physical constraints
    area = project.get_areaconstraints()
    area.set_density(40)
    area.set_coremargin(1)

    # 5. Assign Lambdalib aliases
    GF180Lambdalib_SinglePort.alias(project)
