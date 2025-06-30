from siliconcompiler import ToolLibrarySchema


class VPRLibrary(ToolLibrarySchema):
    def __init__(self, name: str = None):
        super().__init__()
        self.set_name(name)

        self.define_tool_parameter("vpr", "devicecode", "str", "blah")
        self.define_tool_parameter("vpr", "channelwidth", "int", "blah")

        self.define_tool_parameter("vpr", "registers", "[str]", "blah")
        self.define_tool_parameter("vpr", "brams", "[str]", "blah")
        self.define_tool_parameter("vpr", "dsps", "[str]", "blah")

        self.define_tool_parameter("vpr", "archfile", "file", "blah")
        self.define_tool_parameter("vpr", "graphfile", "file", "blah")

        self.define_tool_parameter("vpr", "clock_model", "<ideal,route,dedicated_network>", "blah")

    def set_vpr_devicecode(self, name: str):
        return self.set("tool", "vpr", "devicecode", name)

    def set_vpr_channelwidth(self, width: int):
        return self.set("tool", "vpr", "channelwidth", width)

    def add_vpr_registertype(self, name: str = None, clobber: bool = False):
        if clobber:
            return self.set("tool", "vpr", "registers", name)
        else:
            return self.add("tool", "vpr", "registers", name)

    def add_vpr_bramtype(self, name: str = None, clobber: bool = False):
        if clobber:
            return self.set("tool", "vpr", "brams", name)
        else:
            return self.add("tool", "vpr", "brams", name)

    def add_vpr_dsptype(self, name: str = None, clobber: bool = False):
        if clobber:
            return self.set("tool", "vpr", "dsps", name)
        else:
            return self.add("tool", "vpr", "dsps", name)

    def set_vpr_archfile(self, file: str, dataroot: str = None):
        if not dataroot:
            dataroot = self._get_active("package")
        with self.active_dataroot(dataroot):
            return self.set("tool", "vpr", "archfile", file)

    def set_vpr_graphfile(self, file: str, dataroot: str = None):
        if not dataroot:
            dataroot = self._get_active("package")
        with self.active_dataroot(dataroot):
            return self.set("tool", "vpr", "graphfile", file)

    def set_vpr_clockmodel(self, model: str):
        return self.set("tool", "vpr", "clock_model", model)
