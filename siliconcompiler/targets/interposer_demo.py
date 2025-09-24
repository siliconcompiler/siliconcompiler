from siliconcompiler import ASICProject

from lambdapdk.interposer import Interposer_3ML_0400
from lambdapdk.interposer.libs.bumps import BumpLibrary

from siliconcompiler.flows import interposerflow
from siliconcompiler.flows import drcflow


####################################################
# Target Setup
####################################################
def setup(project: ASICProject):
    '''
    Interposer Demo Target
    '''

    # 1. Load PDK and Libraries
    project.set_pdk(Interposer_3ML_0400())
    project.set_mainlib(BumpLibrary())

    # 2. Load flows
    project.set_flow(interposerflow.InterposerFlow())
    project.add_dep(drcflow.DRCFlow())

    # 3. Set default targets

    # 4. Timing corners
    scenario = project.constraint.timing.make_scenario("typical")
    scenario.add_libcorner("typical")
    scenario.set_pexcorner("typical")
    scenario.add_check(["setup", "hold", "power"])

    project.set_asic_delaymodel("nldm")

    # 5. Physical constraints
    area = project.constraint.area
    area.set_density(40)
    area.set_coremargin(1)

    # 5. Assign Lambdalib aliases
