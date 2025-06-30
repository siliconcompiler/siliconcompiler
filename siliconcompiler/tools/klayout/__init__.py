from siliconcompiler.library import ToolLibrarySchema
from siliconcompiler import PDKSchema


class KLayoutPDK(PDKSchema):
    def __init__(self):
        super().__init__()

        self.define_tool_parameter("klayout", "units", "float", "stream units for klayout")
        self.define_tool_parameter("klayout", "hide_layers", "[str]", "list of layers to initially hide")


class KLayoutLibrary(ToolLibrarySchema):
    def __init__(self):
        super().__init__()

        self.define_tool_parameter("klayout", "allow_missing_cell", "[str]", "cells")
