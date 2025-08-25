from siliconcompiler.tools.opensta import OpenSTATask


class ReportLibraryTask(OpenSTATask):
    '''
    Report information about the timing libraries.
    '''
    def task(self):
        return "report_libraries"

    def setup(self):
        super().setup()

        self.set_script("sc_report_libraries.tcl")
