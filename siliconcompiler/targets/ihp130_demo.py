from siliconcompiler import ASICProject
from siliconcompiler.flows import asicflow, synflow

from lambdapdk.ihp130.libs.sg13g2_stdcell import IHP130StdCell_1p2
from lambdapdk.ihp130.libs.sg13g2_sram import IHP130Lambdalib_SinglePort
from lambdapdk.ihp130.libs.sg13g2_io import IHP130LambdaLib_IO_1p2


####################################################
# Target Setup
####################################################
def setup(project: ASICProject, syn_np=1, floorplan_np=1, physyn_np=1, place_np=1, cts_np=1,
          route_np=1,
          timing_np=1):
    """
          Configure an ASICProject for the IHP130 demo target.
          
          Sets the project's main standard-cell library, selects ASIC and synthesis flows, sets the PDK to "ihp130",
          creates three timing scenarios ("slow", "typical", "fast") with corresponding library corners, PEX corner "typical",
          and checks ("setup", "power", "hold"), sets the ASIC delay model to "nldm", applies area constraints (density and core margin),
          and registers IHP130 lambdalib aliases with the project.
          """

    # 1. Load Libraries
    project.set_mainlib(IHP130StdCell_1p2())

    # 2. Load flows
    project.set_flow(asicflow.ASICFlow())
    project.add_dep(synflow.SynthesisFlow())

    # 3. Set default targets
    project.set_pdk("ihp130")

    # 4. Timing corners
    scenario = project.constraint.timing.make_scenario("slow")
    scenario.add_libcorner("slow")
    scenario.set_pexcorner("typical")
    scenario.add_check("setup")
    scenario = project.constraint.timing.make_scenario("typical")
    scenario.add_libcorner("typical")
    scenario.set_pexcorner("typical")
    scenario.add_check("power")
    scenario = project.constraint.timing.make_scenario("fast")
    scenario.add_libcorner("fast")
    scenario.set_pexcorner("typical")
    scenario.add_check("hold")

    project.set_asic_delaymodel("nldm")

    # 5. Physical constraints
    area = project.constraint.area
    area.set_density(40)
    area.set_coremargin(4.8)

    # 5. Assign Lambdalib aliases
    IHP130Lambdalib_SinglePort.alias(project)
    IHP130LambdaLib_IO_1p2.alias(project)
