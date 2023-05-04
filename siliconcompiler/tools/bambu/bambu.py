'''
The primary objective of the PandA project is to develop a usable framework that will
enable the research of new ideas in the HW-SW Co-Design field.

The PandA framework includes methodologies supporting the research on high-level synthesis
of hardware accelerators, on parallelism extraction for embedded systems, on hardware/software
partitioning and mapping, on metrics for performance estimation of embedded software
applications and on dynamic reconfigurable devices.

Documentation: https://github.com/ferrandi/PandA-bambu

Sources: https://github.com/ferrandi/PandA-bambu

Installation: https://panda.dei.polimi.it/?page_id=88
'''

from siliconcompiler.tools.bambu import convert


####################################################################
# Make Docs
####################################################################
def make_docs(chip):
    convert.setup(chip)
    return chip


def parse_version(stdout):
    # Long multiline output, but second-to-last line looks like:
    # Version: PandA 0.9.6 - Revision 5e5e306b86383a7d85274d64977a3d71fdcff4fe-main
    version_line = stdout.split('\n')[-3]
    return version_line.split()[2]


################################
#  Custom runtime options
################################
def runtime_options(chip):

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    cmdlist = []

    for value in chip.find_files('option', 'idir'):
        cmdlist.append('-I' + value)
    for value in chip.get('option', 'define'):
        cmdlist.append('-D' + value)
    for value in chip.find_files('input', 'hll', 'c', step=step, index=index):
        cmdlist.append(value)

    cmdlist.append('--top-fname=' + chip.top())

    return cmdlist
