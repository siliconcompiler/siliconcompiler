from siliconcompiler.tools.opensta import OpenSTATask


class CheckLibraryTask(OpenSTATask):
    '''
    Check setup information about the timing libraries and report the
    characteristics (pins, capacitance, drive resistance, intrinsic delay)
    of every library cell.
    '''
    def task(self):
        return "check_libraries"

    def setup(self):
        self.set_threads(1)

        super().setup()

        self.set_script("sc_check_library.tcl")
