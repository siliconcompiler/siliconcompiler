from typing import Optional
from siliconcompiler.tools.klayout import KLayoutTask
from siliconcompiler.tools.klayout.screenshot import ScreenshotParams


class ExportTask(KLayoutTask, ScreenshotParams):
    def __init__(self):
        super().__init__()

        self.add_parameter("stream", "<gds,oas>", "Extension to use for stream generation",
                           defvalue="gds")
        self.add_parameter("timestamps", "bool", "Export GDSII with timestamps", defvalue=True)
        self.add_parameter("screenshot", "bool",
                           "true/false: true will cause KLayout to generate a screenshot of "
                           "the layout", defvalue=True)

    def set_klayout_stream(self, stream: str,
                           step: Optional[str] = None,
                           index: Optional[str] = None):
        """
        Sets the stream format for generation.

        Args:
            stream (str): The stream format to use.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "stream", stream, step=step, index=index)

    def set_klayout_timestamps(self, enable: bool,
                               step: Optional[str] = None,
                               index: Optional[str] = None):
        """
        Enables or disables exporting GDSII with timestamps.

        Args:
            enable (bool): Whether to enable timestamps.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "timestamps", enable, step=step, index=index)

    def set_klayout_screenshot(self, enable: bool,
                               step: Optional[str] = None,
                               index: Optional[str] = None):
        """
        Enables or disables generating a screenshot of the layout.

        Args:
            enable (bool): Whether to generate a screenshot.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "screenshot", enable, step=step, index=index)

    def task(self):
        return "export"

    def setup(self):
        super().setup()

        self.set_script("klayout_export.py")

        if f"{self.design_topmodule}.def" in self.get_files_from_input_nodes():
            self.add_input_file(ext="def")
        else:
            for lib, fileset in self.project.get_filesets():
                if lib.has_file(fileset=fileset, filetype="def"):
                    self.add_required_key(lib, "fileset", fileset, "file", "def")
                    break

        self.add_required_key("var", "stream")
        self.add_required_key("var", "timestamps")
        self.add_required_key("var", "screenshot")

        default_stream = self.get("var", "stream")

        self.add_output_file(ext=default_stream)
        self.add_output_file(ext="lyt")
        self.add_output_file(ext="lyp")

        sc_stream_order = [default_stream, *[s for s in ("gds", "oas") if s != default_stream]]
        req_set = False
        for s in sc_stream_order:
            if self.pdk.valid("pdk", "layermapfileset", "klayout", "def", s):
                self.add_required_key(self.pdk, "pdk", "layermapfileset", "klayout", "def", s)
                req_set = True
                break
        if not req_set:
            self.add_required_key(self.pdk, "pdk", "layermapfileset", "klayout", "def", "klayout")

        for lib in self.project.get("asic", "asiclib"):
            lib_requires_stream = True
            if self.project.valid('library', lib, "tool", "klayout", 'allow_missing_cell') and \
                    self.project.get('library', lib, "tool", "klayout", 'allow_missing_cell'):
                lib_requires_stream = False

            req_set = False
            libobj = self.project.get_library(lib)
            for s in sc_stream_order:
                for fileset in libobj.get("asic", "aprfileset"):
                    if libobj.valid("fileset", fileset, "file", s):
                        self.add_required_key(libobj, "fileset", fileset, "file", s)
                        req_set = True
                if req_set:
                    break
            req_set = False
            for fileset in libobj.get("asic", "aprfileset"):
                if libobj.valid("fileset", fileset, "file", "lef"):
                    self.add_required_key(libobj, "fileset", fileset, "file", "lef")
                    req_set = True

            if not req_set and lib_requires_stream:
                self.add_required_key(libobj, "fileset", libobj.get("asic", "aprfileset")[0],
                                      "file", default_stream)
