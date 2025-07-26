from siliconcompiler.library import ToolLibrarySchema


class KLayoutLibrary(ToolLibrarySchema):
    def __init__(self):
        super().__init__()

        self.define_tool_parameter("klayout", "allow_missing_cell", "[str]", "cells")
