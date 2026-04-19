from siliconcompiler import ShowTask as BaseShowTask
from siliconcompiler.tools.openroad import OpenROADTask
from siliconcompiler.tools.openroad.open import OpenTask


class ShowTask(OpenTask, BaseShowTask):
    '''
    Show a design in openroad
    '''
    def __init__(self):
        super().__init__()

    def setup(self):
        super().setup()

        self.set_script("sc_show.tcl")

    def runtime_options(self):
        options = super().runtime_options()
        options.append("-gui")
        return options


class Show3DBloxTask(BaseShowTask, OpenROADTask):
    '''
    Show a 3D view of the design in openroad
    '''
    def __init__(self):
        super().__init__()

    def task(self) -> str:
        return "show3dblox"

    def setup(self):
        super().setup()
        self.set_threads()
        self.set_script("sc_show_3dblox.tcl")

    def get_supported_task_extentions(self):
        return ["3dbx"]

    def runtime_options(self):
        options = super().runtime_options()
        try:
            options.remove("-exit")
        except ValueError:
            pass
        options.append("-gui")
        return options
