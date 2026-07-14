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

        # sc_check_library.tcl reads the per-corner liberty files and the yosys /
        # openroad standard-cell setup for every logic library; declare the keys
        # it accesses as required so they are hashed (cache) and copied
        # (remote runs).
        delay_model = self.project.get("asic", "delaymodel")
        for asiclib in self.project.get("asic", "asiclib"):
            lib = self.project.get_library(asiclib)

            # per-corner liberty files
            for scenario in self.project.constraint.timing.get_scenario().values():
                for corner in scenario.get_libcorner(self.step, self.index):
                    if not lib.valid("asic", "libcornerfileset", corner, delay_model):
                        continue
                    self.add_required_key(lib, "asic", "libcornerfileset", corner, delay_model)
                    for fileset in lib.get("asic", "libcornerfileset", corner, delay_model):
                        self.add_required_key(lib, "fileset", fileset, "file", "liberty")

            # yosys / openroad standard-cell setup parameters
            for tool, params in (
                    ("yosys", ("driver_cell", "buffer_cell", "tiehigh_cell", "tielow_cell",
                               "abc_clock_multiplier", "abc_constraint_load")),
                    ("openroad", ("tiehigh_cell", "tielow_cell"))):
                for param in params:
                    if lib.valid("tool", tool, param) and lib.get("tool", tool, param):
                        self.add_required_key(lib, "tool", tool, param)
