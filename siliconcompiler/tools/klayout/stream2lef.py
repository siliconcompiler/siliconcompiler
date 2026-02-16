from typing import Optional
from siliconcompiler.tools.klayout import KLayoutTask


class Stream2LefTask(KLayoutTask):
    def __init__(self):
        super().__init__()

        self.add_parameter("stream", "<gds,oas>", "Extension to use for stream generation",
                           defvalue="gds")
        self.add_parameter("ignore_cells", "{str}", "Cells to ignore during export")
        self.add_parameter("class_name", "str", "Class name for the LEF macro", defvalue="BLOCK")
        self.add_parameter("site", "str", "Site name for the LEF macro")
        self.add_parameter("symmetry", "{<X,Y,R90>}", "Symmetry for the LEF macro, e.g. X Y R90",
                           defvalue=["X", "Y", "R90"])

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

    def set_klayout_classname(self, class_name: str,
                              step: Optional[str] = None,
                              index: Optional[str] = None):
        """
        Sets the class name for the LEF macro.

        Args:
            class_name (str): The class name for the LEF macro.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "class_name", class_name, step=step, index=index)

    def set_klayout_site(self, site: str,
                         step: Optional[str] = None,
                         index: Optional[str] = None):
        """
        Sets the site name for the LEF macro.

        Args:
            site (str): The site name for the LEF macro.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "site", site, step=step, index=index)

    def add_klayout_symmetry(self, symmetry: str,
                             step: Optional[str] = None,
                             index: Optional[str] = None,
                             clobber: bool = False):
        """
        Adds a symmetry to the LEF macro.

        Args:
            symmetry (str): The symmetry to add.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
            clobber (bool, optional): Whether to overwrite existing symmetry.
        """
        if clobber:
            self.set("var", "symmetry", symmetry, step=step, index=index)
        else:
            self.add("var", "symmetry", symmetry, step=step, index=index)

    def add_klayout_ignorecells(self, ignore_cells: str,
                                step: Optional[str] = None,
                                index: Optional[str] = None,
                                clobber: bool = False):
        """
        Sets the cells to ignore during export.

        Args:
            ignore_cells (str): The cells to ignore during export.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
            clobber (bool, optional): Whether to overwrite existing configuration.
        """
        if clobber:
            self.set("var", "ignore_cells", ignore_cells, step=step, index=index)
        else:
            self.add("var", "ignore_cells", ignore_cells, step=step, index=index)

    def task(self):
        return "stream2lef"

    def setup(self):
        super().setup()

        self.set_script("klayout_stream2lef.py")

        self.add_required_key("var", "stream")
        default_stream = self.get("var", "stream")

        if f"{self.design_topmodule}.{default_stream}" in self.get_files_from_input_nodes():
            self.add_input_file(ext=default_stream)
        else:
            for lib, fileset in self.project.get_filesets():
                if lib.has_file(fileset=fileset, filetype=default_stream):
                    self.add_required_key(lib, "fileset", fileset, "file", default_stream)
                    break

        self.add_required_key("var", "class_name")
        self.add_required_key("var", "symmetry")
        if self.get("var", "site"):
            self.add_required_key("var", "site")
        if self.get("var", "ignore_cells"):
            self.add_required_key("var", "ignore_cells")

        self.add_output_file(ext="lef")

        for s in ("gds", "oas"):
            if self.pdk.valid("pdk", "layermapfileset", "klayout", "def", s):
                self.add_required_key(self.pdk, "pdk", "layermapfileset", "klayout", "def", s)
                for fileset in self.pdk.get("pdk", "layermapfileset", "klayout", "def", s):
                    self.add_required_key(self.pdk, "fileset", fileset, "file", "layermap")
                break
