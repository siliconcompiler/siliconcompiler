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

from typing import List, Union

from siliconcompiler.library import StdCellLibrarySchema
from siliconcompiler.pdk import PDKSchema


class OpenROADPDK(PDKSchema):
    """
    Schema for defining technology-specific parameters for the OpenROAD tool.

    This class extends the base PDKSchema to manage various settings related
    to physical design, such as routing layers, pin layers, and global
    routing derating factors, specifically for the OpenROAD tool.
    """
    def __init__(self):
        super().__init__()

        self.define_tool_parameter("openroad", "rclayer_signal", "str",
                                   "The name of the signal layer to be used for RC extraction.")
        self.define_tool_parameter("openroad", "rclayer_clock", "str",
                                   "The name of the clock layer to be used for RC extraction.")

        self.define_tool_parameter("openroad", "pin_layer_horizontal", "[str]",
                                   "A list of layers designated for horizontal pins.")
        self.define_tool_parameter("openroad", "pin_layer_vertical", "[str]",
                                   "A list of layers designated for vertical pins.")

        self.define_tool_parameter("openroad", "globalroutingderating", "{(str,float)}",
                                   "A set of layer-specific derating factors for global routing.")

        self.define_tool_parameter("openroad", "rcx_maxlayer", "str",
                                   "Max layer to generate an OpenRCX extraction bench for.")

    def set_openroad_rclayers(self, signal: str = None, clock: str = None):
        """
        Sets the signal and/or clock layers for RC extraction.

        Args:
            signal (str, optional): The name of the signal layer. Defaults to None.
            clock (str, optional): The name of the clock layer. Defaults to None.
        """
        if signal:
            self.set("tool", "openroad", "rclayer_signal", signal)
        if clock:
            self.set("tool", "openroad", "rclayer_clock", clock)

    def unset_openroad_globalroutingderating(self):
        """
        Unsets the global routing derating parameter.
        """
        self.unset("tool", "openroad", "globalroutingderating")

    def set_openroad_globalroutingderating(self, layer: str, derating: float,
                                           clobber: bool = False):
        """
        Sets a global routing derating factor for a specific layer.

        Args:
            layer (str): The name of the layer.
            derating (float): The derating factor to apply.
            clobber (bool, optional): If True, overwrites the existing derating factor for the
                                      layer.
                                      If False, adds a new derating factor. Defaults to False.
        """
        if clobber:
            return self.set("tool", "openroad", "globalroutingderating", (layer, derating))
        else:
            return self.add("tool", "openroad", "globalroutingderating", (layer, derating))

    def add_openroad_pinlayers(self,
                               horizontal: Union[str, List[str]] = None,
                               vertical: Union[str, List[str]] = None,
                               clobber: bool = False):
        """
        Adds horizontal and/or vertical pin layers.

        Args:
            horizontal (Union[str, List[str]], optional): The horizontal pin layer(s) to add.
                    Defaults to None.
            vertical (Union[str, List[str]], optional): The vertical pin layer(s) to add.
                Defaults to None.
            clobber (bool, optional): If True, overwrites the existing lists. Defaults to False.
        """
        if clobber:
            if horizontal:
                self.set("tool", "openroad", "pin_layer_horizontal", horizontal)
            if vertical:
                self.set("tool", "openroad", "pin_layer_vertical", vertical)
        else:
            if horizontal:
                self.add("tool", "openroad", "pin_layer_horizontal", horizontal)
            if vertical:
                self.add("tool", "openroad", "pin_layer_vertical", vertical)

    def set_openroad_rcxmaxlayer(self, layer: str):
        """
        Sets the maximum layer for OpenRCX extraction bench generation.

        This parameter defines the highest routing layer to be considered during
        RC extraction.

        Args:
            layer (str): The name of the top-most layer to be used for RC extraction.
        """
        self.set("tool", "openroad", "rcx_maxlayer", layer)


class OpenROADStdCellLibrary(StdCellLibrarySchema):
    """
    Schema for defining standard cell library parameters for the OpenROAD tool.

    This class extends the base StdCellLibrarySchema to manage various settings
    related to physical design, such as tie cells, placement settings, routing,
    and power grid configuration, specifically for the OpenROAD tool.
    """
    def __init__(self):
        super().__init__()

        self.define_tool_parameter("openroad", "tiehigh_cell", "(str,str)",
                                   "A tuple specifying the tie-high cell name and its output port.")
        self.define_tool_parameter("openroad", "tielow_cell", "(str,str)",
                                   "A tuple specifying the tie-low cell name and its output port.")

        self.define_tool_parameter("openroad", "place_density", "float",
                                   "The target placement density for the design.")

        self.define_tool_parameter("openroad", "global_cell_padding", "int",
                                   "Padding to be applied to cells during global placement.",
                                   defvalue=0)
        self.define_tool_parameter("openroad", "detailed_cell_padding", "int",
                                   "Padding to be applied to cells during detailed placement.",
                                   defvalue=0)

        self.define_tool_parameter("openroad", "macro_placement_halo", "(float,float)",
                                   "A tuple for the X and Y dimensions of the halo around macros "
                                   "during placement.")

        self.define_tool_parameter("openroad", "tracks", "file",
                                   "The file containing track definitions for routing.")
        self.define_tool_parameter("openroad", "tapcells", "file",
                                   "The file containing tap cell definitions.")
        self.define_tool_parameter("openroad", "global_connect", "[file]",
                                   "A list of global connect files.")
        self.define_tool_parameter("openroad", "power_grid", "[file]",
                                   "A list of power grid files.")

        self.define_tool_parameter("openroad", "scan_chain_cells", "[str]",
                                   "A list of cells used for scan chain insertion.")
        self.define_tool_parameter("openroad", "multibit_ff_cells", "[str]",
                                   "A list of multibit flip-flop cells.")

    def set_openroad_tiehigh_cell(self, cell: str, output_port: str):
        """
        Sets the tie-high cell and its output port.

        Args:
            cell (str): The name of the tie-high cell.
            output_port (str): The name of the output port.
        """
        self.set("tool", "openroad", "tiehigh_cell", (cell, output_port))

    def set_openroad_tielow_cell(self, cell: str, output_port: str):
        """
        Sets the tie-low cell and its output port.

        Args:
            cell (str): The name of the tie-low cell.
            output_port (str): The name of the output port.
        """
        self.set("tool", "openroad", "tielow_cell", (cell, output_port))

    def set_openroad_placement_density(self, density: float):
        """
        Sets the target placement density.

        Args:
            density (float): The target placement density, a value between 0.0 and 1.0.
        """
        self.set("tool", "openroad", "place_density", density)

    def set_openroad_cell_padding(self, global_place: int, detailed_place: int):
        """
        Sets the cell padding for both global and detailed placement.

        Args:
            global_place (int): Padding for global placement.
            detailed_place (int): Padding for detailed placement.
        """
        self.set("tool", "openroad", "global_cell_padding", global_place)
        self.set("tool", "openroad", "detailed_cell_padding", detailed_place)

    def set_openroad_macro_placement_halo(self, x: float, y: float):
        """
        Sets the halo dimensions for macro placement.

        Args:
            x (float): The halo dimension in the x-direction.
            y (float): The halo dimension in the y-direction.
        """
        self.set("tool", "openroad", "macro_placement_halo", (x, y))

    def set_openroad_tracks_file(self, file: str, dataroot: str = None):
        """
        Sets the file for track definitions.

        Args:
            file (str): The path to the tracks file.
            dataroot (str, optional): The data root directory. Defaults to the active package.
        """
        if not dataroot:
            dataroot = self._get_active("package")
        with self.active_dataroot(dataroot):
            self.set("tool", "openroad", "tracks", file)

    def set_openroad_tapcells_file(self, file: str, dataroot: str = None):
        """
        Sets the file for tap cell definitions.

        Args:
            file (str): The path to the tap cells file.
            dataroot (str, optional): The data root directory. Defaults to the active package.
        """
        if not dataroot:
            dataroot = self._get_active("package")
        with self.active_dataroot(dataroot):
            self.set("tool", "openroad", "tapcells", file)

    def add_openroad_global_connect_file(self, file: Union[str, List[str]], dataroot: str = None,
                                         clobber: bool = False):
        """
        Adds a global connect file to the list.

        Args:
            file (Union[str, List[str]]): The path to the global connect file or a list of paths.
            dataroot (str, optional): The data root directory. Defaults to the active package.
            clobber (bool, optional): If True, overwrites existing values. Defaults to False.
        """
        if not dataroot:
            dataroot = self._get_active("package")
        with self.active_dataroot(dataroot):
            if clobber:
                self.set("tool", "openroad", "global_connect", file)
            else:
                self.add("tool", "openroad", "global_connect", file)

    def add_openroad_power_grid_file(self, file: Union[str, List[str]], dataroot: str = None,
                                     clobber: bool = False):
        """
        Adds a power grid file to the list.

        Args:
            file (Union[str, List[str]]): The path to the power grid file or a list of paths.
            dataroot (str, optional): The data root directory. Defaults to the active package.
            clobber (bool, optional): If True, overwrites existing values. Defaults to False.
        """
        if not dataroot:
            dataroot = self._get_active("package")
        with self.active_dataroot(dataroot):
            if clobber:
                self.set("tool", "openroad", "power_grid", file)
            else:
                self.add("tool", "openroad", "power_grid", file)

    def add_openroad_scan_chain_cells(self, cells: Union[str, List[str]], clobber: bool = False):
        """
        Adds scan chain cells to the list.

        Args:
            cells (Union[str, List[str]]): A cell name or a list of cell names.
            clobber (bool, optional): If True, overwrites existing values. Defaults to False.
        """
        if clobber:
            self.set("tool", "openroad", "scan_chain_cells", cells)
        else:
            self.add("tool", "openroad", "scan_chain_cells", cells)

    def add_openroad_multibit_flipflops(self, cells: Union[str, List[str]], clobber: bool = False):
        """
        Adds multibit flip-flop cells to the list.

        Args:
            cells (Union[str, List[str]]): A cell name or a list of cell names.
            clobber (bool, optional): If True, overwrites existing values. Defaults to False.
        """
        if clobber:
            self.set("tool", "openroad", "multibit_ff_cells", cells)
        else:
            self.add("tool", "openroad", "multibit_ff_cells", cells)


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
