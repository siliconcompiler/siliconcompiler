'''
OpenROAD is an automated physical design platform for
integrated circuit design with a complete set of features
needed to translate a synthesized netlist to a tapeout ready
GDSII.

Documentation: https://openroad.readthedocs.io/

Sources: https://github.com/The-OpenROAD-Project/OpenROAD

Installation: https://github.com/The-OpenROAD-Project/OpenROAD
'''
from siliconcompiler.tools._common import get_tool_task


####################################################################
# Make Docs
####################################################################
def make_docs(chip):
    from siliconcompiler.targets import asap7_demo
    chip.use(asap7_demo)


################################
# Setup Tool (pre executable)
################################
def setup(chip, exit=True, clobber=False):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'exe', 'openroad')
    chip.set('tool', tool, 'vswitch', '-version')
    chip.set('tool', tool, 'version', '>=v2.0-17598', clobber=clobber)
    chip.set('tool', tool, 'format', 'tcl', clobber=clobber)

    option = [
        "-no_init",
        "-metrics", "reports/metrics.json"
    ]

    # exit automatically in batch mode and not breakpoint
    if exit and \
       not chip.get('option', 'breakpoint', step=step, index=index):
        option.append("-exit")

    chip.set('tool', tool, 'task', task, 'option', option,
             step=step, index=index, clobber=clobber)

    chip.set('tool', tool, 'task', task, 'refdir',
             'tools/openroad/scripts',
             step=step, index=index, package='siliconcompiler')

    # basic warning and error grep check on logfile
    chip.set('tool', tool, 'task', task, 'regex', 'warnings',
             r'^\[WARNING|Warning',
             step=step, index=index, clobber=clobber)
    chip.set('tool', tool, 'task', task, 'regex', 'errors',
             r'^\[ERROR',
             step=step, index=index, clobber=clobber)

    chip.set('tool', tool, 'task', task, 'var', 'debug_level',
             'list of "tool key level" to enable debugging of OpenROAD',
             field='help')

    if chip.get('option', 'nodisplay'):
        # Tells QT to use the offscreen platform if nodisplay is used
        chip.set('tool', tool, 'task', task, 'env',
                 'QT_QPA_PLATFORM', 'offscreen',
                 step=step, index=index)


################################
# Version Check
################################
def parse_version(stdout):
    # stdout will be in one of the following forms:
    # - 1 08de3b46c71e329a10aa4e753dcfeba2ddf54ddd
    # - 1 v2.0-880-gd1c7001ad
    # - v2.0-1862-g0d785bd84

    # strip off the "1" prefix if it's there
    version = stdout.split()[-1]

    pieces = version.split('-')
    if len(pieces) > 1:
        # strip off the hash in the new version style
        return '-'.join(pieces[:-1])
    else:
        return pieces[0]


def normalize_version(version):
    if '.' in version:
        return version.lstrip('v')
    else:
        return '0'


##################################################
if __name__ == "__main__":
    chip = make_docs()
    chip.write_manifest("openroad.json")
