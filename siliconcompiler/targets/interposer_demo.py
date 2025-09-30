# Import necessary classes from the siliconcompiler framework and the LambdaPDK.
from siliconcompiler import ASIC

from lambdapdk.interposer import Interposer_3ML_0400
from lambdapdk.interposer.libs.bumps import BumpLibrary

from siliconcompiler.flows import interposerflow
from siliconcompiler.flows import drcflow


####################################################
# Target Setup Function
####################################################
def interposer_demo(project: ASIC):
    """
    Configure a siliconcompiler project for generating a passive interposer layout.

    This configures the project for a passive interposer target by selecting the interposer PDK
    and bump library, setting an interposer-focused flow with DRC dependency, creating a basic
    "typical" timing scenario (libcorner, pexcorner, and setup/hold/power checks), setting the
    ASIC delay model to "nldm", and applying physical area constraints
    (40% routing density and 1 unit core margin). No lambdalib/IP aliases are defined.

    Parameters:
        * project (ASIC): The siliconcompiler project to configure.
    """

    # 1. Load Interposer PDK and Bump Library
    # Sets the process development kit specifically designed for the interposer's
    # manufacturing process and loads the library defining the physical
    # characteristics of the connection bumps.
    project.set_pdk(Interposer_3ML_0400())
    project.set_mainlib(BumpLibrary())

    # 2. Configure Compilation Flows
    # The 'interposerflow' is a specialized flow for generating the layout of a
    # passive interposer. It focuses on routing between bump locations.
    # A 'drcflow' (Design Rule Check) is added as a dependency to ensure the
    # final layout adheres to the PDK's manufacturing rules.
    project.set_flow(interposerflow.InterposerFlow())
    project.add_dep(drcflow.DRCFlow())

    # 3. Define a Basic Timing Scenario
    # While passive interposers do not have active logic for traditional setup/hold
    # timing analysis, a basic scenario is defined. This can be used for signal
    # integrity analysis, delay extraction, or to satisfy tool requirements.
    scenario = project.constraint.timing.make_scenario("typical")
    scenario.add_libcorner("typical")
    scenario.set_pexcorner("typical")
    # Checks for setup, hold, and power are included mainly for tool compatibility.
    scenario.add_check(["setup", "hold", "power"])

    # Set a delay model, though its application is limited in a passive context.
    project.set_asic_delaymodel("nldm")

    # 4. Define Physical Design Constraints
    # These constraints guide the routing tools.
    area = project.constraint.area
    # Target a routing density of 40%.
    area.set_density(40)
    # Set a margin of 1 unit (e.g., microns) around the interposer area.
    area.set_coremargin(1)

    # 5. Assign Lambdalib Aliases
    # No specialized IP aliases (like SRAM or IOs) are needed for this
    # simple passive interposer target.
