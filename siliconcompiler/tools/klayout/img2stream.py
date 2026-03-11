from typing import Optional
from siliconcompiler.tools.klayout import KLayoutTask


class Img2StreamTask(KLayoutTask):
    def __init__(self):
        super().__init__()

        self.add_parameter("stream", "<gds,oas>", "Extension to use for stream generation",
                           defvalue="gds")
        self.add_parameter("imageformat", "<png,jpg>", "Image format for input files",
                           defvalue="png")
        self.add_parameter("minsize", "float", "Minimum shape size for image processing",
                           units="um")
        self.add_parameter("targetwidth", "float", "Target width for the image",
                           units="um")
        self.add_parameter("layer", "(int,int)", "Stream layer to putput image on")
        self.add_parameter("invert", "bool", "Invert the polarity of the image", defvalue=False)
        self.add_parameter("darkissolid", "bool", "Treat dark colors as a solid", defvalue=True)
        self.add_parameter("timestamp", "bool", "Export GDSII with timestamps", defvalue=True)

    def set_klayout_timestamp(self, enable: bool,
                              step: Optional[str] = None,
                              index: Optional[str] = None):
        """
        Enables or disables exporting GDSII with timestamps.

        Args:
            enable (bool): Whether to enable timestamps.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "timestamp", enable, step=step, index=index)

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

    def set_klayout_imageformat(self, format: str,
                                step: Optional[str] = None,
                                index: Optional[str] = None):
        """
        Sets the image format for generation.

        Args:
            format (str): The image format to use.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "imageformat", format, step=step, index=index)

    def set_klayout_minsize(self, minsize: float,
                            step: Optional[str] = None,
                            index: Optional[str] = None):
        """
        Sets the minimum shape size for generation.

        Args:
            minsize (float): The minimum shape size to use.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "minsize", minsize, step=step, index=index)

    def set_klayout_targetwidth(self, targetwidth: float,
                                step: Optional[str] = None,
                                index: Optional[str] = None):
        """Sets the target width for generation.
        Args:
            targetwidth (float): The target width to use.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "targetwidth", targetwidth, step=step, index=index)

    def set_klayout_layer(self, layer: int, purpose: int = 0,
                          step: Optional[str] = None,
                          index: Optional[str] = None):
        """
        Sets the layer for generation.
        Args:
            layer (int): The layer to use.
            purpose (int, optional): The purpose of the layer.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "layer", (layer, purpose), step=step, index=index)

    def set_klayout_invert(self, invert: bool,
                           step: Optional[str] = None,
                           index: Optional[str] = None):
        """
        Sets the invert flag for generation.
        Args:
            invert (bool): Whether to invert the image.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "invert", invert, step=step, index=index)

    def set_klayout_darkissolid(self, darkissolid: bool,
                                step: Optional[str] = None,
                                index: Optional[str] = None):
        """
        Sets the darkissolid flag for generation.
        Args:
            darkissolid (bool): Whether to treat dark colors as a solid.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "darkissolid", darkissolid, step=step, index=index)

    def task(self):
        return "image2stream"

    def setup(self):
        super().setup()

        self.set_script("klayout_img2stream.py")

        self.add_required_key("var", "imageformat")
        imageformat = self.get("var", "imageformat")
        self.add_required_key("var", "stream")
        default_stream = self.get("var", "stream")

        self.add_required_key("var", "minsize")
        self.add_required_key("var", "targetwidth")
        self.add_required_key("var", "layer")
        self.add_required_key("var", "invert")
        self.add_required_key("var", "darkissolid")
        self.add_required_key("var", "timestamp")

        self.add_output_file(ext=f"{default_stream}.gz")

        if f"{self.design_topmodule}.{imageformat}" in self.get_files_from_input_nodes():
            self.add_input_file(ext=imageformat)
        else:
            for lib, fileset in self.project.get_filesets():
                if lib.has_file(fileset=fileset, filetype=imageformat):
                    self.add_required_key(lib, "fileset", fileset, "file", imageformat)
                    break
