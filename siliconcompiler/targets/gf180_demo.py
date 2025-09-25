from siliconcompiler import ASICProject
from siliconcompiler.flows import asicflow, synflow

from lambdapdk.gf180 import GF180_5LM_1TM_9K_9t
from lambdapdk.gf180.libs.gf180mcu import GF180_MCU_9T_5LMLibrary
from lambdapdk.gf180.libs.gf180sram import GF180Lambdalib_SinglePort
from lambdapdk.gf180.libs.gf180io import GF180Lambdalib_IO_5LM


####################################################
# Target Setup
####################################################
def setup(project: ASICProject, syn_np=1, floorplan_np=1, physyn_np=1, place_np=1, cts_np=1,
          route_np=1,
          timing_np=1):
    """
          Configure an ASICProject for the GlobalFoundries 180nm demo target.
          
          Sets the PDK and ASIC libraries, configures the ASIC and synthesis flows, creates three timing scenarios (slow, typical, fast) with associated corners and pin voltages, sets the ASIC delay model, applies area constraints (density and core margin), and registers Lambdalib aliases.
          
          Parameters:
              project (ASICProject): Project instance to configure.
              syn_np (int): Suggested parallelism for synthesis stages (default 1).
              floorplan_np (int): Suggested parallelism for floorplanning stages (default 1).
              physyn_np (int): Suggested parallelism for physical synthesis stages (default 1).
              place_np (int): Suggested parallelism for placement stages (default 1).
              cts_np (int): Suggested parallelism for clock-tree synthesis stages (default 1).
              route_np (int): Suggested parallelism for routing stages (default 1).
              timing_np (int): Suggested parallelism for timing analysis stages (default 1).
          """

    # 1. Load PDK and Libraries
    project.set_pdk(GF180_5LM_1TM_9K_9t())
    project.add_asiclib(GF180_MCU_9T_5LMLibrary())
    project.set_mainlib(GF180_MCU_9T_5LMLibrary())

    # 2. Load flows
    project.set_flow(asicflow.ASICFlow())
    project.add_dep(synflow.SynthesisFlow())

    # 3. Set default targets

    # 4. Timing corners
    scenario = project.constraint.timing.make_scenario("slow")
    scenario.add_libcorner("slow")
    scenario.set_pexcorner("wst")
    scenario.add_check("setup")
    scenario.set_pin_voltage("VDD", 4.5)
    scenario = project.constraint.timing.make_scenario("typical")
    scenario.add_libcorner("typical")
    scenario.set_pexcorner("typ")
    scenario.add_check("power")
    scenario.set_pin_voltage("VDD", 5.0)
    scenario = project.constraint.timing.make_scenario("fast")
    scenario.add_libcorner("fast")
    scenario.set_pexcorner("bst")
    scenario.add_check("hold")
    scenario.set_pin_voltage("VDD", 5.5)

    project.set_asic_delaymodel("nldm")

    # 5. Physical constraints
    area = project.constraint.area
    area.set_density(40)
    area.set_coremargin(1)

    # 5. Assign Lambdalib aliases
    GF180Lambdalib_SinglePort.alias(project)
    GF180Lambdalib_IO_5LM.alias(project)
