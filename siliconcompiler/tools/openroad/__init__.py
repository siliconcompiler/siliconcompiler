'''
OpenROAD is an automated physical design platform for
integrated circuit design with a complete set of features
needed to translate a synthesized netlist to a tapeout ready
GDSII.

Documentation: https://openroad.readthedocs.io/

Sources: https://github.com/The-OpenROAD-Project/OpenROAD

Installation: https://github.com/The-OpenROAD-Project/OpenROAD
'''
from typing import List, Union, Optional

from siliconcompiler import StdCellLibrary
from siliconcompiler import PDK
from siliconcompiler.asic import ASICTask


class OpenROADPDK(PDK):
    """
    Schema for defining technology-specific parameters for the OpenROAD tool.

    This class extends the base PDK to manage various settings related
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

        self.define_tool_parameter("openroad", "drt_process_node", "str",
                                   "Detailed routing node name")
        self.define_tool_parameter("openroad", "drt_disable_via_gen", "bool",
                                   "true/false, when true turns off via generation in detailed "
                                   "router and only uses the specified tech vias")
        self.define_tool_parameter("openroad", "drt_repair_pdn_vias", "str",
                                   "Via layer to repair after detailed routing")

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

    def set_openroad_processnode(self, node: str):
        """Sets the detailed routing process node name.

        Args:
            node (str): The name of the process node.
        """
        self.set("tool", "openroad", "drt_process_node", node)

    def set_openroad_detailedroutedisableviagen(self, value: bool):
        """Enables or disables automatic via generation in the detailed router.

        When set to True, the router will only use vias explicitly defined in the
        technology LEF, rather than generating new ones.

        Args:
            value (bool): The boolean value to set. True disables via generation.
        """
        self.set("tool", "openroad", "drt_disable_via_gen", value)

    def set_openroad_detailedrouteviarepair(self, layer: str):
        """Specifies the via layer to repair after detailed routing.

        This is used to fix issues on a specific via layer in the power delivery
        network (PDN) post-routing.

        Args:
            layer (str): The name of the via layer to repair.
        """
        self.set("tool", "openroad", "drt_repair_pdn_vias", layer)


class OpenROADStdCellLibrary(StdCellLibrary):
    """
    Schema for defining standard cell library parameters for the OpenROAD tool.

    This class extends the base StdCellLibrary to manage various settings
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
        self.define_tool_parameter("openroad", "global_connect_fileset", "{str}",
                                   "A list of global connect files.")
        self.define_tool_parameter("openroad", "power_grid_fileset", "{str}",
                                   "A list of power grid files.")

        self.define_tool_parameter("openroad", "scan_chain_cells", "{str}",
                                   "A list of cells used for scan chain insertion.")
        self.define_tool_parameter("openroad", "multibit_ff_cells", "{str}",
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
        with self.active_dataroot(self._get_active_dataroot(dataroot)):
            self.set("tool", "openroad", "tracks", file)

    def set_openroad_tapcells_file(self, file: str, dataroot: str = None):
        """
        Sets the file for tap cell definitions.

        Args:
            file (str): The path to the tap cells file.
            dataroot (str, optional): The data root directory. Defaults to the active package.
        """
        with self.active_dataroot(self._get_active_dataroot(dataroot)):
            self.set("tool", "openroad", "tapcells", file)

    def add_openroad_globalconnectfileset(self, fileset: Union[str, List[str]] = None,
                                          clobber: bool = False):
        """Configures the global connect fileset for the OpenROAD tool.

        This method defines the fileset used for global pin connections
        (e.g., tying power/ground pins) in the OpenROAD flow.

        Args:
            fileset (Union[str, List[str]]): The name of the fileset to use.
                If not provided, the active fileset is used.
            clobber (bool, optional): If True, overwrites any existing
                configuration. If False, adds to it. Defaults to False.
        """
        if not fileset:
            fileset = self._get_active("fileset")

        self._assert_fileset(fileset)

        if clobber:
            self.set("tool", "openroad", "global_connect_fileset", fileset)
        else:
            self.add("tool", "openroad", "global_connect_fileset", fileset)

    def add_openroad_powergridfileset(self, fileset: Union[str, List[str]] = None,
                                      clobber: bool = False):
        """Configures the power grid definition fileset for the OpenROAD tool.

        This method defines the fileset used for generating the power grid
        (e.g., PDN configuration files) in the OpenROAD flow.

        Args:
            fileset (Union[str, List[str]]): The name of the fileset to use.
                If not provided, the active fileset is used.
            clobber (bool, optional): If True, overwrites any existing
                configuration. If False, adds to it. Defaults to False.
        """
        if not fileset:
            fileset = self._get_active("fileset")

        self._assert_fileset(fileset)

        if clobber:
            self.set("tool", "openroad", "power_grid_fileset", fileset)
        else:
            self.add("tool", "openroad", "power_grid_fileset", fileset)

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


class OpenROADTask(ASICTask):
    """
    Base class for tasks involving the OpenROAD EDA tool chain.

    This class provides common functionality for configuring OpenROAD execution,
    such as setting up debug levels for internal tools.
    """
    def __init__(self):
        super().__init__()

        self.add_parameter("debug_level", "{(str,str,int)}",
                           'list of "tool key level" to enable debugging of OpenROAD')

    def add_openroad_debuglevel(self, tool: str, category: str, level: int,
                                step: Optional[str] = None, index: Optional[str] = None,
                                clobber: bool = False) -> None:
        """
        Configures the debug logging level for a specific OpenROAD tool and category.

        Args:
            tool: The name of the OpenROAD tool (e.g., "GRT", "PSM").
            category: The specific debug category or keyword within the tool.
            level: The integer verbosity level for the debug output.
            step: The specific step to apply this configuration to.
            index: The specific index to apply this configuration to.
            clobber: If True, overwrites the existing debug level configuration.
                     If False, appends this configuration to the existing list.
        """
        if clobber:
            self.set("var", "debug_level", (tool, category, level), step=step, index=index)
        else:
            self.add("var", "debug_level", (tool, category, level), step=step, index=index)

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

        if self.project.get('option', 'nodisplay'):
            # Tells QT to use the offscreen platform if nodisplay is used
            self.set_environmentalvariable("QT_QPA_PLATFORM", "offscreen")

        if self.get("var", "debug_level"):
            self.add_required_key("var", "debug_level")

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

    @classmethod
    def make_docs(cls):
        from siliconcompiler import Flowgraph, Design, ASIC
        from siliconcompiler.scheduler import SchedulerNode
        from siliconcompiler.targets import freepdk45_demo
        design = Design("<design>")
        with design.active_fileset("docs"):
            design.set_topmodule("top")
        proj = ASIC(design)
        proj.add_fileset("docs")
        freepdk45_demo(proj)
        flow = Flowgraph("docsflow")
        flow.node("<step>", cls(), index="<index>")
        proj.set_flow(flow)

        node = SchedulerNode(proj, "<step>", "<index>")
        node.setup()
        return node.task
