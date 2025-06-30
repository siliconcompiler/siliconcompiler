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

from siliconcompiler.library import StdCellLibrarySchema
from siliconcompiler.pdk import PDKSchema
from siliconcompiler.tool import ASICTaskSchema


class OpenROADPDK(PDKSchema):
    def __init__(self):
        super().__init__()

        self.define_tool_parameter("openroad", "rclayer_signal", "str", "blah")
        self.define_tool_parameter("openroad", "rclayer_clock", "str", "blah")

        self.define_tool_parameter("openroad", "pin_layer_horizontal", "[str]", "blah")
        self.define_tool_parameter("openroad", "pin_layer_vertical", "[str]", "blah")
        self.define_tool_parameter("openroad", "globalroutingderating", "{(str,float)}", "blah")

    def set_openroad_rclayers(self, signal: str = None, clock: str = None):
        if signal:
            self.set("tool", "openroad", "rclayer_signal", signal)
        if clock:
            self.set("tool", "openroad", "rclayer_clock", clock)

    def set_openroad_globalroutingderating(self, layer: str, derating: float):
        return self.add("tool", "openroad", "globalroutingderating", (layer, derating))

    def add_openroad_pinlayers(self, horizontal=None, veritcal=None):
        if horizontal:
            self.add("tool", "openroad", "pin_layer_horizontal", horizontal)
        if veritcal:
            self.add("tool", "openroad", "pin_layer_vertical", veritcal)


class OpenROADStdCellLibrarySchema(StdCellLibrarySchema):
    def __init__(self):
        super().__init__()

        self.define_tool_parameter("openroad", "tiehigh_cell", "(str,str)",  "long-blah")
        self.define_tool_parameter("openroad", "tielow_cell", "(str,str)", "long-blah")

        self.define_tool_parameter("openroad", "place_density", "float", "long-blah")

        self.define_tool_parameter("openroad", "global_cell_padding", "int", "long-blah", defvalue=0)
        self.define_tool_parameter("openroad", "detailed_cell_padding", "int", "long-blah", defvalue=0)

        self.define_tool_parameter("openroad", "macro_placement_halo", "(float,float)", "long-blah")

        self.define_tool_parameter("openroad", "tracks", "file", "long-blah")
        self.define_tool_parameter("openroad", "tapcells", "file", "long-blah")
        self.define_tool_parameter("openroad", "global_connect", "[file]", "long-blah")
        self.define_tool_parameter("openroad", "power_grid", "[file]", "long-blah")

        self.define_tool_parameter("openroad", "scan_chain_cells", "[str]", "scan chain cells")
        self.define_tool_parameter("openroad", "multibit_ff_cells", "[str]", "multibit flipflops cells")

    def set_openroad_tiehigh_cell(self, cell, output_port):
        self.set("tool", "openroad", "tiehigh_cell", (cell, output_port))

    def set_openroad_tielow_cell(self, cell, output_port):
        self.set("tool", "openroad", "tielow_cell", (cell, output_port))

    def set_openroad_placement_density(self, density):
        self.set("tool", "openroad", "place_density", density)

    def set_openroad_cell_padding(self, global_place, detailed_place):
        self.set("tool", "openroad", "global_cell_padding", global_place)
        self.set("tool", "openroad", "detailed_cell_padding", detailed_place)

    def set_openroad_macro_placement_halo(self, x, y):
        self.set("tool", "openroad", "macro_placement_halo", (x, y))

    def set_openroad_tracks_file(self, file):
        self.set("tool", "openroad", "tracks", file)

    def set_openroad_tapcells_file(self, file):
        self.set("tool", "openroad", "tapcells", file)

    def add_openroad_global_connect_file(self, file):
        self.add("tool", "openroad", "global_connect", file)

    def add_openroad_power_grid_file(self, file):
        self.add("tool", "openroad", "power_grid", file)

    def add_openroad_scan_chain_cells(self, cells):
        self.add("tool", "openroad", "scan_chain_cells", cells)

    def add_openroad_multibit_flipflops(self, cells):
        self.add("tool", "openroad", "multibit_ff_cells", cells)


class OpenROADTask(ASICTaskSchema):
    def __init__(self):
        super().__init__()

        self.add_parameter("debug_level", "{(str,str,int)}", 'list of "tool key level" to enable debugging of OpenROAD')

    def tool(self):
        return "openroad"

    def setup(self):
        super().setup()

        self.set_exe("openroad", vswitch="-version", format="tcl")
        self.add_version(">=v2.0-17598")

        self.set_dataroot("openroad-ref", __file__)
        with self.active_dataroot("openroad-ref"):
            self.set_refdir("scripts")

        self.add_regex("warnings", r'^\[WARNING|^Warning')
        self.add_regex("errors", r'^\[ERROR')

        if self.schema().get('option', 'nodisplay'):
            # Tells QT to use the offscreen platform if nodisplay is used
            self.set_environmentalvariable("QPA_QT_PLATFORM", "offscreen")

    def parse_version(self, stdout):
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

    def normalize_version(self, version):
        if '.' in version:
            return version.lstrip('v')
        else:
            return '0'

    def add_debuglevel(self, tool, category, level, clobber=False):
        if clobber:
            self.set("var", "debug_level", (tool, category, level))
        else:
            self.add("var", "debug_level", (tool, category, level))

    def unset_debuglevel(self):
        self.unset("var", "debug_level")

    def runtime_options(self):
        options = super().runtime_options()
        options.append("-no_init")
        options.extend(["-metrics", "reports/metrics.json"])

        if not self.has_breakpoint():
            options.append("-exit")

        return options


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
