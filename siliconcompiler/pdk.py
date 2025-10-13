import math

from typing import Tuple, Optional, Union, List

from siliconcompiler.schema import EditableSchema, Parameter, Scope, BaseSchema
from siliconcompiler.schema.utils import trim

from siliconcompiler.library import ToolLibrarySchema
from siliconcompiler.schema_support.pathschema import PathSchema
from siliconcompiler.schema_support.filesetschema import FileSetSchema


class PDK(ToolLibrarySchema):
    """
    A schema for managing and validating Process Design Kit (PDK) configurations.

    This class defines the structured parameters that constitute a PDK,
    such as foundry information, process node, metal stackups, and various
    technology files required for different EDA tools. It extends the
    ToolLibrarySchema to provide a standardized way of describing and
    accessing PDK data within the SiliconCompiler framework.
    """
    def __init__(self, name: Optional[str] = None):
        """
        Initializes a PDK object.

        Args:
            name (str, optional): The name of the PDK. Defaults to None.
        """
        super().__init__()
        self.set_name(name)

        schema = EditableSchema(self)

        schema.insert(
            "pdk", 'foundry',
            Parameter(
                'str',
                scope=Scope.GLOBAL,
                shorthelp="PDK: foundry name",
                switch="-pdk_foundry 'pdkname <str>'",
                example=["cli: -pdk_foundry 'asap7 virtual'",
                         "api: pdk.set('pdk', 'asap7', 'foundry', 'virtual')"],
                help=trim("""
                Name of foundry corporation. Examples include intel, gf, tsmc,
                samsung, skywater, virtual. The 'virtual' keyword is reserved for
                simulated non-manufacturable processes.""")))

        schema.insert(
            "pdk", 'node',
            Parameter(
                'float',
                scope=Scope.GLOBAL,
                unit='nm',
                shorthelp="PDK: process node",
                switch="-pdk_node 'pdkname <float>'",
                example=["cli: -pdk_node 'asap7 130'",
                         "api: pdk.set('pdk', 'asap7', 'node', 130)"],
                help=trim("""
                Approximate relative minimum dimension of the process target specified
                in nanometers. The parameter is required for flows and tools that
                leverage the value to drive technology dependent synthesis and APR
                optimization. Node examples include 180, 130, 90, 65, 45, 32, 22 14,
                10, 7, 5, 3.""")))

        schema.insert(
            "pdk", 'stackup',
            Parameter(
                'str',
                scope=Scope.GLOBAL,
                shorthelp="PDK: metal stackups",
                switch="-pdk_stackup 'pdkname <str>'",
                example=["cli: -pdk_stackup 'asap7 2MA4MB2MC'",
                         "api: pdk.add('pdk', 'asap7', 'stackup', '2MA4MB2MC')"],
                help=trim("""
                List of all metal stackups offered in the process node. Older process
                nodes may only offer a single metal stackup, while advanced nodes
                offer a large but finite list of metal stacks with varying combinations
                of metal line pitches and thicknesses. Stackup naming is unique to a
                foundry, but is generally a long string or code. For example, a 10
                metal stackup with two 1x wide, four 2x wide, and 4x wide metals,
                might be identified as 2MA4MB2MC, where MA, MB, and MC denote wiring
                layers with different properties (thickness, width, space). Each
                stackup will come with its own set of routing technology files and
                parasitic models specified in the pdk_pexmodel and pdk_aprtech
                parameters.""")))

        schema.insert(
            "pdk", 'minlayer',
            Parameter(
                'str',
                scope=Scope.GLOBAL,
                shorthelp="PDK: minimum routing layer",
                switch="-pdk_minlayer 'pdk stackup <str>'",
                example=[
                    "cli: -pdk_minlayer 'asap7 2MA4MB2MC M2'",
                    "api: pdk.set('pdk', 'asap7', 'minlayer', '2MA4MB2MC', 'M2')"],
                help=trim("""
                Minimum metal layer to be used for automated place and route
                specified on a per stackup basis.""")))

        schema.insert(
            "pdk", 'maxlayer',
            Parameter(
                'str',
                scope=Scope.GLOBAL,
                shorthelp="PDK: maximum routing layer",
                switch="-pdk_maxlayer 'pdk stackup <str>'",
                example=[
                    "cli: -pdk_maxlayer 'asap7 2MA4MB2MC M8'",
                    "api: pdk.set('pdk', 'asap7', 'maxlayer', 'MA4MB2MC', 'M8')"],
                help=trim("""
                Maximum metal layer to be used for automated place and route
                specified on a per stackup basis.""")))

        schema.insert(
            "pdk", 'wafersize',
            Parameter(
                'float',
                scope=Scope.GLOBAL,
                unit='mm',
                shorthelp="PDK: wafer size",
                switch="-pdk_wafersize 'pdkname <float>'",
                example=["cli: -pdk_wafersize 'asap7 300'",
                         "api: pdk.set('pdk', 'asap7', 'wafersize', 300)"],
                help=trim("""
                Wafer diameter used in wafer based manufacturing process.
                The standard diameter for leading edge manufacturing is 300mm. For
                older process technologies and specialty fabs, smaller diameters
                such as 200, 150, 125, and 100 are common. The value is used to
                calculate dies per wafer and full factory chip costs.""")))

        schema.insert(
            "pdk", 'unitcost',
            Parameter(
                'float',
                scope=Scope.GLOBAL,
                unit='USD',
                shorthelp="PDK: unit cost",
                switch="-pdk_unitcost 'pdkname <float>'",
                example=["cli: -pdk_unitcost 'asap7 10000'",
                         "api: pdk.set('pdk', 'asap7', 'unitcost', 10000)"],
                help=trim("""
                Raw cost per unit shipped by the factory, not accounting for yield
                loss.""")))

        schema.insert(
            "pdk", 'd0',
            Parameter(
                'float',
                scope=Scope.GLOBAL,
                shorthelp="PDK: process defect density",
                switch="-pdk_d0 'pdkname <float>'",
                example=["cli: -pdk_d0 'asap7 0.1'",
                         "api: pdk.set('pdk', 'asap7', 'd0', 0.1)"],
                help=trim("""
                Process defect density (d0) expressed as random defects per cm^2. The
                value is used to calculate yield losses as a function of area, which in
                turn affects the chip full factory costs. Two yield models are
                supported: Poisson (default), and Murphy. The Poisson based yield is
                calculated as dy = exp(-area * d0/100). The Murphy based yield is
                calculated as dy = ((1-exp(-area * d0/100))/(area * d0/100))^2.""")))

        schema.insert(
            "pdk", 'scribe',
            Parameter(
                '(float,float)',
                scope=Scope.GLOBAL,
                unit='mm',
                shorthelp="PDK: horizontal scribe line width",
                switch="-pdk_scribe 'pdkname <(float,float)>'",
                example=["cli: -pdk_scribe 'asap7 (0.1,0.1)'",
                         "api: pdk.set('pdk', 'asap7', 'scribe', (0.1, 0.1))"],
                help=trim("""
                Width of the horizontal and vertical scribe line used during die separation.
                The process is generally completed using a mechanical saw, but can be
                done through combinations of mechanical saws, lasers, wafer thinning,
                and chemical etching in more advanced technologies. The value is used
                to calculate effective dies per wafer and full factory cost.""")))

        schema.insert(
            "pdk", 'edgemargin',
            Parameter(
                'float',
                scope=Scope.GLOBAL,
                unit='mm',
                shorthelp="PDK: wafer edge keep-out margin",
                switch="-pdk_edgemargin 'pdkname <float>'",
                example=[
                    "cli: -pdk_edgemargin 'asap7 1'",
                    "api: pdk.set('pdk', 'asap7', 'edgemargin', 1)"],
                help=trim("""
                Keep-out distance/margin from the edge inwards. The edge
                is prone to chipping and need special treatment that preclude
                placement of designs in this area. The edge value is used to
                calculate effective units per wafer/panel and full factory cost.""")))

        tool = 'default'
        simtype = 'default'
        schema.insert(
            "pdk", 'devmodelfileset', tool, simtype,
            Parameter(
                '[str]',
                scope=Scope.GLOBAL,
                shorthelp="PDK: device models",
                switch="-pdk_devmodel 'pdkname tool simtype stackup <file>'",
                example=[
                    "cli: -pdk_devmodel 'asap7 xyce spice M10 asap7.sp'",
                    "api: pdk.set('pdk', 'asap7', 'devmodelfileset', 'xyce', 'spice', "
                    "'M10', 'asap7.sp')"],
                help=trim("""
                List of filepaths to PDK device models for different simulation
                purposes and for different tools. Examples of device model types
                include spice, aging, electromigration, radiation. An example of a
                'spice' tool is xyce. Device models are specified on a per metal stack
                basis. Process nodes with a single device model across all stacks will
                have a unique parameter record per metal stack pointing to the same
                device model file. Device types and tools are dynamic entries
                that depend on the tool setup and device technology. Pseudo-standardized
                device types include spice, em (electromigration), and aging.""")))

        corner = 'default'
        schema.insert(
            "pdk", 'pexmodelfileset', tool, corner,
            Parameter(
                '[str]',
                scope=Scope.GLOBAL,
                shorthelp="PDK: parasitic TCAD models",
                switch="-pdk_pexmodel 'pdkname tool stackup corner <file>'",
                example=[
                    "cli: -pdk_pexmodel 'asap7 fastcap M10 max wire.mod'",
                    "api: pdk.set('pdk', 'asap7', 'pexmodel', 'fastcap', 'M10', 'max', "
                    "'wire.mod')"],
                help=trim("""
                List of filepaths to PDK wire TCAD models used during automated
                synthesis, APR, and signoff verification. Pexmodels are specified on
                a per metal stack basis. Corner values depend on the process being
                used, but typically include nomenclature such as min, max, nominal.
                For exact names, refer to the DRM. Pexmodels are generally not
                standardized and specified on a per tool basis. An example of pexmodel
                type is 'fastcap'.""")))

        src = 'default'
        dst = 'default'
        schema.insert(
            "pdk", 'layermapfileset', tool, src, dst,
            Parameter(
                '[str]',
                scope=Scope.GLOBAL,
                shorthelp="PDK: layer map file",
                switch="-pdk_layermap 'pdkname tool src dst stackup <file>'",
                example=[
                    "cli: -pdk_layermap 'asap7 klayout db gds M10 asap7.map'",
                    "api: pdk.set('pdk', 'asap7', 'layermap', 'klayout', 'db', 'gds', 'M10', "
                    "'asap7.map')"],
                help=trim("""
                Files describing input/output mapping for streaming layout data from
                one format to another. A foundry PDK will include an official layer
                list for all user entered and generated layers supported in the GDS
                accepted by the foundry for processing, but there is no standardized
                layer definition format that can be read and written by all EDA tools.
                To ensure mask layer matching, key/value type mapping files are needed
                to convert EDA databases to/from GDS and to convert between different
                types of EDA databases. Layer maps are specified on a per metal
                stackup basis. The 'src' and 'dst' can be names of SC supported tools
                or file formats (like 'gds').""")))

        schema.insert(
            "pdk", 'displayfileset', tool,
            Parameter(
                '[str]',
                scope=Scope.GLOBAL,
                shorthelp="PDK: display file",
                switch="-pdk_display 'pdkname tool stackup <file>'",
                example=[
                    "cli: -pdk_display 'asap7 klayout M10 display.lyt'",
                    "api: pdk.set('pdk', 'asap7', 'display', 'klayout', 'M10', 'display.cfg')"],
                help=trim("""
                Display configuration files describing colors and pattern schemes for
                all layers in the PDK. The display configuration file is entered on a
                stackup and tool basis.""")))

        # TODO: create firm list of accepted files
        schema.insert(
            "pdk", 'aprtechfileset', tool,
            Parameter(
                '[str]',
                scope=Scope.GLOBAL,
                shorthelp="PDK: APR technology files",
                switch="-pdk_aprtech 'pdkname tool stackup libarch filetype <file>'",
                example=[
                    "cli: -pdk_aprtech 'asap7 openroad M10 12t lef tech.lef'",
                    "api: pdk.set('pdk', 'asap7', 'aprtech', 'openroad', 'M10', '12t', 'lef', "
                    "'tech.lef')"],
                help=trim("""
                Technology file containing setup information needed to enable DRC clean APR
                for the specified stackup, libarch, and format. The 'libarch' specifies the
                library architecture (e.g. library height). For example a PDK with support
                for 9 and 12 track libraries might have 'libarchs' called 9t and 12t.
                The standard filetype for specifying place and route design rules for a
                process node is through a 'lef' format technology file. The
                'filetype' used in the aprtech is used by the tool specific APR TCL scripts
                to set up the technology parameters. Some tools may require additional
                files beyond the tech.lef file. Examples of extra file types include
                antenna, tracks, tapcell, viarules, and em.""")))

        name = 'default'
        for item in ('lvs', 'drc', 'erc', 'fill'):
            schema.insert(
                "pdk", item, 'runsetfileset', tool, name,
                Parameter(
                    '[str]',
                    scope=Scope.GLOBAL,
                    shorthelp=f"PDK: {item.upper()} runset files",
                    switch=f"-pdk_{item}_runset 'pdkname tool stackup name <file>'",
                    example=[
                        f"cli: -pdk_{item}_runset 'asap7 magic M10 basic $PDK/{item}.rs'",
                        f"api: pdk.set('{item}', 'runset', 'magic', 'M10', 'basic', "
                        f"'$PDK/{item}.rs')"],
                    help=trim(f"""Runset files for {item.upper()} task.""")))

            schema.insert(
                "pdk", item, 'waiverfileset', tool, name,
                Parameter(
                    '[str]',
                    scope=Scope.GLOBAL,
                    shorthelp=f"PDK: {item.upper()} waiver files",
                    switch=f"-pdk_{item}_waiver 'pdkname tool stackup name <file>'",
                    example=[
                        f"cli: -pdk_{item}_waiver 'asap7 magic M10 basic $PDK/{item}.txt'",
                        f"api: pdk.set('{item}', 'waiver', 'magic', 'M10', 'basic', "
                        f"'$PDK/{item}.txt')"],
                    help=trim(f"""Waiver files for {item.upper()} task.""")))

    def set_foundry(self, foundry: str):
        """
        Sets the foundry name for the PDK.

        Args:
            foundry (str): The name of the foundry.
        """
        return self.set("pdk", "foundry", foundry)

    def set_node(self, node: float):
        """
        Sets the process node for the PDK.

        Args:
            node (float): The process node in nanometers.
        """
        return self.set("pdk", "node", node)

    def set_stackup(self, stackup: str):
        """
        Sets the metal stackup for the PDK.

        Args:
            stackup (str): The name of the metal stackup.
        """
        return self.set("pdk", "stackup", stackup)

    def set_wafersize(self, wafersize: float):
        """
        Sets the wafer size for the PDK.

        Args:
            wafersize (float): The wafer diameter in millimeters.
        """
        return self.set("pdk", "wafersize", wafersize)

    def set_unitcost(self, unitcost: float):
        """
        Sets the unit cost for the PDK.

        Args:
            unitcost (float): The unit cost in USD.
        """
        return self.set("pdk", "unitcost", unitcost)

    def set_defectdensity(self, d0: float):
        """
        Sets the process defect density for the PDK.

        Args:
            d0 (float): The defect density (defects per cm^2).
        """
        return self.set("pdk", "d0", d0)

    def set_scribewidth(self, x: float, y: float):
        """
        Sets the scribe line width for the PDK.

        Args:
            x (float): The horizontal scribe width in millimeters.
            y (float): The vertical scribe width in millimeters.
        """
        return self.set("pdk", "scribe", (x, y))

    def set_edgemargin(self, margin: float):
        """
        Sets the wafer edge keep-out margin for the PDK.

        Args:
            margin (float): The edge margin in millimeters.
        """
        return self.set("pdk", "edgemargin", margin)

    def set_aprroutinglayers(self, min: Optional[str] = None, max: Optional[str] = None):
        """
        Sets the minimum and maximum routing layers for the PDK.

        Args:
            min (str, optional): The minimum routing layer name. Defaults to None.
            max (str, optional): The maximum routing layer name. Defaults to None.
        """
        if min:
            self.set("pdk", "minlayer", min)
        if max:
            self.set("pdk", "maxlayer", max)

    def add_aprtechfileset(self, tool: str, fileset: Optional[Union[List[str], str]] = None,
                           clobber: bool = False):
        """
        Adds a fileset containing APR technology files.

        Args:
            tool (str): The name of the tool.
            fileset (str, optional): The name of the fileset. Defaults to None,
                                     which uses the active fileset.
            clobber (bool, optional): If True, overwrites existing entries. Defaults to False.
        """
        if not fileset:
            fileset = self._get_active("fileset")

        self._assert_fileset(fileset)

        if clobber:
            return self.set("pdk", "aprtechfileset", tool, fileset)
        else:
            return self.add("pdk", "aprtechfileset", tool, fileset)

    def add_layermapfileset(self, tool: str, src: str, dst: str,
                            fileset: Optional[Union[List[str], str]] = None,
                            clobber: bool = False):
        """
        Adds a fileset containing layer map files.

        Args:
            tool (str): The name of the tool.
            src (str): The source format or tool name.
            dst (str): The destination format or tool name.
            fileset (str, optional): The name of the fileset. Defaults to None,
                                     which uses the active fileset.
            clobber (bool, optional): If True, overwrites existing entries. Defaults to False.
        """
        if not fileset:
            fileset = self._get_active("fileset")

        self._assert_fileset(fileset)

        if clobber:
            return self.set("pdk", "layermapfileset", tool, src, dst, fileset)
        else:
            return self.add("pdk", "layermapfileset", tool, src, dst, fileset)

    def add_displayfileset(self, tool: str, fileset: Optional[Union[List[str], str]] = None,
                           clobber: bool = False):
        """
        Adds a fileset containing display configuration files.

        Args:
            tool (str): The name of the tool.
            fileset (str, optional): The name of the fileset. Defaults to None,
                                     which uses the active fileset.
            clobber (bool, optional): If True, overwrites existing entries. Defaults to False.
        """
        if not fileset:
            fileset = self._get_active("fileset")

        self._assert_fileset(fileset)

        if clobber:
            return self.set("pdk", "displayfileset", tool, fileset)
        else:
            return self.add("pdk", "displayfileset", tool, fileset)

    def add_devmodelfileset(self, tool: str, type: str,
                            fileset: Optional[Union[List[str], str]] = None,
                            clobber: bool = False):
        """
        Adds a fileset containing device model files.

        Args:
            tool (str): The name of the tool.
            type (str): The type of the device model (e.g., 'spice').
            fileset (str, optional): The name of the fileset. Defaults to None,
                                     which uses the active fileset.
            clobber (bool, optional): If True, overwrites existing entries. Defaults to False.
        """
        if not fileset:
            fileset = self._get_active("fileset")

        self._assert_fileset(fileset)

        if clobber:
            return self.set("pdk", "devmodelfileset", tool, type, fileset)
        else:
            return self.add("pdk", "devmodelfileset", tool, type, fileset)

    def add_pexmodelfileset(self, tool: str, corner: str,
                            fileset: Optional[Union[List[str], str]] = None,
                            clobber: bool = False):
        """
        Adds a fileset containing parasitic extraction (pex) model files.

        Args:
            tool (str): The name of the tool.
            corner (str): The corner name (e.g., 'min', 'max').
            fileset (str, optional): The name of the fileset. Defaults to None,
                                     which uses the active fileset.
            clobber (bool, optional): If True, overwrites existing entries. Defaults to False.
        """
        if not fileset:
            fileset = self._get_active("fileset")

        self._assert_fileset(fileset)

        if clobber:
            return self.set("pdk", "pexmodelfileset", tool, corner, fileset)
        else:
            return self.add("pdk", "pexmodelfileset", tool, corner, fileset)

    def add_runsetfileset(self, type: str, tool: str, name: str,
                          fileset: Optional[Union[List[str], str]] = None,
                          clobber: bool = False):
        """
        Adds a fileset containing a runset for a specific verification task.

        Args:
            type (str): The type of task (e.g., 'lvs', 'drc').
            tool (str): The name of the tool.
            name (str): The name of the runset.
            fileset (str, optional): The name of the fileset. Defaults to None,
                                     which uses the active fileset.
            clobber (bool, optional): If True, overwrites existing entries. Defaults to False.
        """
        if not fileset:
            fileset = self._get_active("fileset")

        self._assert_fileset(fileset)

        if clobber:
            return self.set("pdk", type, "runsetfileset", tool, name, fileset)
        else:
            return self.add("pdk", type, "runsetfileset", tool, name, fileset)

    def add_waiverfileset(self, type: str, tool: str, name: str,
                          fileset: Optional[Union[List[str], str]] = None,
                          clobber: bool = False):
        """
        Adds a fileset containing waiver files for a specific verification task.

        Args:
            type (str): The type of task (e.g., 'lvs', 'drc').
            tool (str): The name of the tool.
            name (str): The name of the waiver set.
            fileset (str, optional): The name of the fileset. Defaults to None,
                                     which uses the active fileset.
            clobber (bool, optional): If True, overwrites existing entries. Defaults to False.
        """
        if not fileset:
            fileset = self._get_active("fileset")

        self._assert_fileset(fileset)

        if clobber:
            return self.set("pdk", type, "waiverfileset", tool, name, fileset)
        else:
            return self.add("pdk", type, "waiverfileset", tool, name, fileset)

    @classmethod
    def _getdict_type(cls) -> str:
        """
        Returns the meta data for getdict
        """

        return PDK.__name__

    def calc_yield(self, diearea: float, model: str = 'poisson') -> float:
        '''Calculates raw die yield.

        Calculates the raw yield of the design as a function of design area
        and d0 defect density. Calculation can be done based on the poisson
        model (default) or the murphy model. The die area and the d0
        parameters are taken from the pdk dictionary.

        * Poisson model: dy = exp(-area * d0/100).
        * Murphy model: dy = ((1-exp(-area * d0/100))/(area * d0/100))^2.

        Args:
            diearea (float): The area of the die in square micrometers (um^2).
            model (string): Model to use for calculation (poisson or murphy)

        Returns:
            float: Design yield percentage.

        Examples:
            >>> yield = pdk.calc_yield(1500.0)
            # Calculates yield for a 1500 um^2 die.
        '''
        d0: Optional[float] = self.get('pdk', 'd0')
        if d0 is None:
            raise ValueError(f"[{','.join([*self._keypath, 'pdk', 'd0'])}] has not been set")

        # diearea is um^2, but d0 looking for cm^2
        diearea_cm2 = diearea / (10000.0**2)
        d0 /= 100.0

        if model == 'poisson':
            dy = math.exp(-diearea_cm2 * d0)
        elif model == 'murphy':
            argument = diearea_cm2 * d0
            if argument == 0:
                return 1.0
            dy = ((1 - math.exp(-argument)) / argument)**2
        else:
            raise ValueError(f'Unknown yield model: {model}')

        return dy

    def calc_dpw(self, diewidth: float, dieheight: float) -> int:
        '''Calculates dies per wafer.

        Calculates the gross dies per wafer based on the design area, wafersize,
        wafer edge margin, and scribe lines. The calculation is done by starting
        at the center of the wafer and placing as many complete design
        footprints as possible within a legal placement area.

        Args:
            diewidth (float): The width of the die in micrometers (um).
            dieheight (float): The height of the die in micrometers (um).

        Returns:
            int: Number of gross dies per wafer.

        Examples:
            >>> dpw = pdk.calc_dpw(1000.0, 1500.0)
            # Calculates dies per wafer for a 1000x1500 um die.
        '''
        # PDK information
        wafersize: Optional[float] = self.get('pdk', 'wafersize')

        if wafersize is None:
            raise ValueError(f"[{','.join([*self._keypath, 'pdk', 'wafersize'])}] has not been set")

        edgemargin: Optional[float] = self.get('pdk', 'edgemargin')
        if edgemargin is None:
            edgemargin = 0.0

        scribe: Tuple[Optional[float], Optional[float]] = self.get('pdk', 'scribe')
        if scribe:
            hscribe, vscribe = scribe
        else:
            hscribe, vscribe = None, None

        if hscribe is None:
            hscribe = 0.0

        if vscribe is None:
            vscribe = 0.0

        # Convert to mm
        diewidth_mm = diewidth / 1000.0
        dieheight_mm = dieheight / 1000.0

        # Derived parameters
        radius = wafersize / 2.0 - edgemargin
        if radius <= 0:
            return 0

        stepwidth = diewidth_mm + hscribe
        stepheight = dieheight_mm + vscribe

        if stepwidth <= 0 or stepheight <= 0:
            return 0

        # Raster dies out from center until you touch edge margin
        # Work quadrant by quadrant
        dies = 0
        # This algorithm is a simple raster scan from the center, which is an
        # approximation. More complex algorithms could yield slightly higher counts.
        for quad in ('q1', 'q2', 'q3', 'q4'):
            x = 0
            y = 0
            if quad == "q1":
                xincr = stepwidth
                yincr = stepheight
            elif quad == "q2":
                xincr = -stepwidth
                yincr = stepheight
            elif quad == "q3":
                xincr = -stepwidth
                yincr = -stepheight
            elif quad == "q4":
                xincr = stepwidth
                yincr = -stepheight

            while math.hypot(0, y) < radius:
                y = y + yincr
                x = xincr
                while math.hypot(x, y) < radius:
                    x = x + xincr
                    dies = dies + 1

        return dies

    def _generate_doc(self, doc,
                      ref_root: str = "",
                      key_offset: Optional[Tuple[str, ...]] = None,
                      detailed: bool = True):
        from .schema.docs.utils import build_section
        docs = []

        if not key_offset:
            key_offset = ("PDK",)

        # Show dataroot
        dataroot = PathSchema._generate_doc(self, doc, ref_root)
        if dataroot:
            docs.append(dataroot)

        # Show package information
        package = self.package._generate_doc(doc, ref_root=ref_root, key_offset=key_offset)
        if package:
            docs.append(package)

        # Show filesets
        fileset = FileSetSchema._generate_doc(self, doc, ref_root=ref_root, key_offset=key_offset)
        if fileset:
            docs.append(fileset)

        # Show PDK
        pdk_sec = build_section("PDK", f"{ref_root}-pdkinfo")
        pdk_sec += BaseSchema._generate_doc(self.get("pdk", field="schema"),
                                            doc,
                                            ref_root=f"{ref_root}-pdkinfo",
                                            key_offset=key_offset,
                                            detailed=False)
        docs.append(pdk_sec)

        # Show tool information
        tools_sec = ToolLibrarySchema._generate_doc(self, doc,
                                                    ref_root=ref_root,
                                                    key_offset=key_offset)
        if tools_sec:
            docs.append(tools_sec)

        return docs
