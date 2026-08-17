'''
Klayout is a production grade viewer and editor of GDSII and
Oasis data with customizable Python and Ruby interfaces.

Documentation: https://www.klayout.de

Sources: https://github.com/KLayout/klayout

Installation: https://www.klayout.de/build.html
'''
import json
import platform
import shutil

import os.path

from pathlib import Path
from typing import List, Optional, Union

from siliconcompiler import PDK, StdCellLibrary, sc_open
from siliconcompiler.asic import ASICTask


class KLayoutPDK(PDK):
    """
    Schema for defining technology-specific parameters for the KLayout tool.

    This class extends the base PDK to manage settings related to
    KLayout, such as stream units and which layers to hide on initial display.
    """
    def __init__(self):
        super().__init__()

        self.define_tool_parameter("klayout", "units", "float<0.0..>",
                                   "The stream units for KLayout.")
        self.define_tool_parameter("klayout", "hide_layers", "{str}",
                                   "A list of layer names to initially hide when "
                                   "displaying a layout.")
        self.define_tool_parameter("klayout", "drc_params", "{(str,str)}",
                                   "Set of parameters to include for a particular drc deck, in the "
                                   "form (deck name, parameter).")

    def set_klayout_units(self, units: float):
        """
        Sets the stream units for KLayout.

        Args:
            units (float): The stream unit value.
        """
        self.set("tool", "klayout", "units", units)

    def add_klayout_hidelayers(self, layer: Union[str, List[str]], clobber: bool = False):
        """
        Adds one or more layers to the list of layers to be hidden.

        Args:
            layer (Union[str, List[str]]): The layer name or a list of layer names.
            clobber (bool, optional): If True, overwrites the existing list of hidden layers.
                                      If False, appends to the list. Defaults to False.
        """
        if clobber:
            self.set("tool", "klayout", "hide_layers", layer)
        else:
            self.add("tool", "klayout", "hide_layers", layer)

    def add_klayout_drcparam(self, deck: str, param: Union[str, List[str]], clobber: bool = False):
        """
        Adds one or more parameter to the DRC deck definition.

        Args:
            deck (str): name of the DRC deck.
            param (Union[str, List[str]]): Parameters for a the specified deck.
            clobber (bool, optional): If True, overwrites the existing list of parameters.
                                      If False, appends to the list. Defaults to False.
        """
        if isinstance(param, str):
            param = [param]
        if clobber:
            self.unset("tool", "klayout", "drc_params")

        for p in param:
            self.add("tool", "klayout", "drc_params", (deck, p))


class KLayoutLibrary(StdCellLibrary):
    """
    Schema for defining standard cell library parameters for the KLayout tool.

    This class extends the base StdCellLibrary to manage settings for
    KLayout, such as defining cells that are allowed to be missing from the
    final stream file without generating an error.
    """
    def __init__(self):
        super().__init__()

        self.define_tool_parameter("klayout", "allow_missing_cell", "{str}",
                                   "A list of cells that are allowed to be empty "
                                   "in the final stream file.")

    def add_klayout_allowmissingcell(self, cell: Union[str, List[str]], clobber: bool = False):
        """
        Adds one or more cell names to the list of cells allowed to be missing.

        Args:
            cell (Union[str, List[str]]): The cell name or a list of cell names.
            clobber (bool, optional): If True, overwrites the existing list.
                                      If False, appends to the list. Defaults to False.
        """
        if clobber:
            self.set("tool", "klayout", "allow_missing_cell", cell)
        else:
            self.add("tool", "klayout", "allow_missing_cell", cell)


class KLayoutTask(ASICTask):
    def __init__(self):
        super().__init__()

        self.add_parameter("hide_layers", "[str]",
                           "list of layers to hide, in addition to the layers hidden by the PDK")

    def add_klayout_hidelayers(self, layer: Union[str, List[str]],
                               step: Optional[str] = None,
                               index: Optional[Union[str, int]] = None,
                               clobber: bool = False):
        """
        Adds one or more layers to hide when displaying or screenshotting a layout.

        These are hidden in addition to the layers named by
        :meth:`.KLayoutPDK.add_klayout_hidelayers`. A layer can be named either by
        name or as a ``<layer>/<datatype>`` pair.

        Args:
            layer (Union[str, List[str]]): The layer name or a list of layer names.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
            clobber (bool, optional): If True, overwrites the existing list of hidden layers.
                                      If False, appends to the list. Defaults to False.
        """
        if clobber:
            return self.set("var", "hide_layers", layer, step=step, index=index)
        return self.add("var", "hide_layers", layer, step=step, index=index)

    def tool(self):
        return "klayout"

    def parse_version(self, stdout):
        # KLayout 0.26.11
        return stdout.split()[1]

    def _add_hidelayers_required_keys(self) -> None:
        """
        Declares the layer visibility keys read by show() in klayout_show.py.

        The layers to hide are the union of the PDK and task settings, so both keys are
        declared when they hold a value.
        """
        if self.get("var", "hide_layers"):
            self.add_required_key("var", "hide_layers")
        if self.pdk.get("tool", "klayout", "hide_layers"):
            self.add_required_key(self.pdk, "tool", "klayout", "hide_layers")

    def _add_technology_files(self) -> None:
        """
        Declares the files read by technology() in klayout_utils.py.

        The technology (.lyt) and layer properties (.lyp) files written by a previous node
        take precedence over the PDK files, but are only available when an input node
        provides them, so they are declared as inputs only in that case. The PDK files
        used when they are not available are declared required so they are hashed (cache)
        and copied (remote runs).
        """
        input_files = self.get_files_from_input_nodes()
        for ext in ("lyt", "lyp"):
            if f"{self.design_topmodule}.{ext}" in input_files:
                self.add_input_file(ext=ext)

        if self.pdk.valid("pdk", "layermapfileset", "klayout", "def", "klayout") and \
                self.pdk.get("pdk", "layermapfileset", "klayout", "def", "klayout"):
            self.add_required_key(self.pdk, "pdk", "layermapfileset", "klayout", "def", "klayout")
            for fileset in self.pdk.get("pdk", "layermapfileset", "klayout", "def", "klayout"):
                if self.pdk.has_file(fileset=fileset, filetype="layermap"):
                    self.add_required_key(self.pdk, "fileset", fileset, "file", "layermap")

        if self.pdk.valid("pdk", "displayfileset", "klayout") and \
                self.pdk.get("pdk", "displayfileset", "klayout"):
            self.add_required_key(self.pdk, "pdk", "displayfileset", "klayout")
            for fileset in self.pdk.get("pdk", "displayfileset", "klayout"):
                if self.pdk.has_file(fileset=fileset, filetype="display"):
                    self.add_required_key(self.pdk, "fileset", fileset, "file", "display")

        if self.pdk.get("tool", "klayout", "units"):
            self.add_required_key(self.pdk, "tool", "klayout", "units")

    def setup(self):
        super().setup()

        klayout_exe = 'klayout'
        if self.project.option.scheduler.get_name(step=self.step, index=self.index) != 'docker':
            if platform.system() == 'Windows':
                klayout_exe = 'klayout_app.exe'
                if not shutil.which(klayout_exe):
                    loc_dir = os.path.join(Path.home(), 'AppData', 'Roaming', 'KLayout')
                    global_dir = os.path.join(os.path.splitdrive(Path.home())[0],
                                              os.path.sep,
                                              'Program Files (x86)',
                                              'KLayout')
                    if os.path.isdir(loc_dir):
                        self.set_path(loc_dir)
                    elif os.path.isdir(global_dir):
                        self.set_path(global_dir)
            elif platform.system() == 'Darwin':
                klayout_exe = 'klayout'
                if not shutil.which(klayout_exe):
                    klayout_dir = os.path.join(os.path.sep,
                                               'Applications',
                                               'klayout.app',
                                               'Contents',
                                               'MacOS')
                    # different install directory when installed using Homebrew
                    klayout_brew_dir = os.path.join(os.path.sep,
                                                    'Applications',
                                                    'KLayout',
                                                    'klayout.app',
                                                    'Contents',
                                                    'MacOS')
                    if os.path.isdir(klayout_dir):
                        self.set_path(klayout_dir)
                    elif os.path.isdir(klayout_brew_dir):
                        self.set_path(klayout_brew_dir)

        self.set_exe(klayout_exe, vswitch=['-zz', '-v'], format="json")
        self.add_version(">=0.28.0")

        self.add_commandline_option(['-z', '-nc', '-rx', '-r'], clobber=True)

        self.set_dataroot("refdir", __file__)
        with self.active_dataroot("refdir"):
            self.set_refdir("scripts")

        self.set_environmentalvariable('PYTHONUNBUFFERED', '1')

        if self.project.option.get_nodisplay():
            # Tells QT to use the offscreen platform if nodisplay is used
            self.set_environmentalvariable('QT_QPA_PLATFORM', 'offscreen')

        self.add_regex("warnings", r'(WARNING|warning)')
        self.add_regex("errors", r'ERROR')

        self.set_threads(1)

    def runtime_options(self):
        options = super().runtime_options()
        options.extend(['-rd', f'SC_KLAYOUT_ROOT={self.find_files("refdir")[0]}'])
        options.extend(['-rd', f'SC_TOOLS_ROOT={os.path.dirname(os.path.dirname(__file__))}'])
        options.extend(['-rd',
                        f'SC_ROOT={os.path.dirname(os.path.dirname(os.path.dirname(__file__)))}'])
        return options

    def post_process(self):
        super().post_process()
        metrics_file = "reports/metrics.json"
        if not os.path.exists(metrics_file):
            return

        with sc_open(metrics_file) as f:
            metrics = json.load(f)

        if "area" in metrics:
            self.record_metric("totalarea", metrics["area"], metrics_file, "um^2")

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


class KLayoutStreamTask(KLayoutTask):
    """
    Base class for KLayout tasks that read or write stream files.

    Collects the stream format and timestamp settings shared by every task that
    produces a GDSII or OASIS file, along with the helpers for naming the files
    that follow from them.
    """
    def __init__(self):
        super().__init__()

        self.add_parameter("stream", "<gds,oas>",
                           "Extension to use for stream generation", defvalue="gds")
        self.add_parameter("timestamps", "bool",
                           "Export GDSII with timestamps", defvalue=True)

    def set_klayout_stream(self, stream: str,
                           step: Optional[str] = None,
                           index: Optional[Union[str, int]] = None):
        """
        Sets the stream format for generation.

        Args:
            stream (str): The stream format to use.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        return self.set("var", "stream", stream, step=step, index=index)

    def _get_klayout_stream(self, step: Optional[str] = None,
                            index: Optional[Union[str, int]] = None) -> str:
        """
        Returns the stream format used for generation.

        Args:
            step (str, optional): The specific step to read this configuration from.
            index (str, optional): The specific index to read this configuration from.
        """
        return self.get("var", "stream", step=step, index=index)

    def set_klayout_timestamps(self, enable: bool,
                               step: Optional[str] = None,
                               index: Optional[Union[str, int]] = None):
        """
        Enables or disables exporting GDSII with timestamps.

        Args:
            enable (bool): Whether to enable timestamps.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        return self.set("var", "timestamps", enable, step=step, index=index)

    def _get_klayout_streamorder(self, step: Optional[str] = None,
                                 index: Optional[Union[str, int]] = None) -> List[str]:
        """
        Returns the supported stream formats, most preferred first.

        Args:
            step (str, optional): The specific step to read this configuration from.
            index (str, optional): The specific index to read this configuration from.
        """
        stream = self._get_klayout_stream(step=step, index=index)
        return [stream, *[other for other in ("gds", "oas") if other != stream]]

    def _add_stream_input_file(self, step: Optional[str] = None,
                               index: Optional[Union[str, int]] = None):
        """
        Declares the stream file this task reads.

        Prefers a compressed stream when an input node provides one, otherwise
        falls back to the uncompressed name.

        Args:
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        stream = self._get_klayout_stream(step=step, index=index)

        if f"{self.design_topmodule}.{stream}.gz" in self.get_files_from_input_nodes():
            return self.add_input_file(ext=f"{stream}.gz", step=step, index=index)
        return self.add_input_file(ext=stream, step=step, index=index)

    def _add_stream_output_file(self, step: Optional[str] = None,
                                index: Optional[Union[str, int]] = None):
        """
        Declares the compressed stream file this task writes.

        Args:
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        stream = self._get_klayout_stream(step=step, index=index)
        return self.add_output_file(ext=f"{stream}.gz", step=step, index=index)

    def setup(self):
        super().setup()

        self.add_required_key("var", "stream")
        self.add_required_key("var", "timestamps")
