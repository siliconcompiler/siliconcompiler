from siliconcompiler import ASICProject
from siliconcompiler.flows import asicflow, synflow

from lambdapdk.asap7.libs.asap7sc7p5t import ASAP7SC7p5RVT, ASAP7SC7p5SLVT, ASAP7SC7p5LVT
from lambdapdk.asap7.libs.fakeram7 import FakeRAM7Lambdalib_SinglePort, FakeRAM7Lambdalib_DoublePort
from lambdapdk.asap7.libs.fakeio7 import FakeIO7Lambdalib_IO


####################################################
# Target Setup
####################################################
def setup(project: ASICProject, syn_np=1, floorplan_np=1, physyn_np=1, place_np=1, cts_np=1,
          route_np=1,
          timing_np=1):
    """
          Configure an ASICProject for the ASAP7 demo target.
          
          This applies ASAP7 libraries, sets ASIC and synthesis flows, configures the PDK to "asap7",
          creates three timing scenarios ("slow", "typical", "fast") with associated library and PEX corners
          and checks, sets the ASIC delay model to "nldm", configures area constraints (density 40, core margin 1),
          and registers FakeRAM/FakeIO lambdalib aliases on the project.
          
          Parameters:
              project (ASICProject): Project instance to configure.
              syn_np (int): Compatibility no-parallel parameter for synthesis (accepted but not used).
              floorplan_np (int): Compatibility no-parallel parameter for floorplanning (accepted but not used).
              physyn_np (int): Compatibility no-parallel parameter for physical synthesis (accepted but not used).
              place_np (int): Compatibility no-parallel parameter for placement (accepted but not used).
              cts_np (int): Compatibility no-parallel parameter for clock tree synthesis (accepted but not used).
              route_np (int): Compatibility no-parallel parameter for routing (accepted but not used).
              timing_np (int): Compatibility no-parallel parameter for timing (accepted but not used).
          """

    # 1. Load Libraries
    project.set_mainlib(ASAP7SC7p5RVT())
    project.add_asiclib(ASAP7SC7p5LVT())
    project.add_asiclib(ASAP7SC7p5SLVT())

    # 2. Load flows
    project.set_flow(asicflow.ASICFlow())
    project.add_dep(synflow.SynthesisFlow())

    # 3. Set default targets
    project.set_pdk("asap7")

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
    FakeRAM7Lambdalib_SinglePort.alias(project)
    FakeRAM7Lambdalib_DoublePort.alias(project)
    FakeIO7Lambdalib_IO.alias(project)
