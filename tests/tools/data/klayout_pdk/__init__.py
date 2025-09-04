from siliconcompiler.tools.klayout import KLayoutPDK


class FauxPDK(KLayoutPDK):
    def __init__(self):
        super().__init__()
        self.set_name("faux")

        self.set_dataroot("root", __file__)

        self.set_stackup("M5")

        self.add_klayout_drcparam("drc", "input=<input>")
        self.add_klayout_drcparam("drc", "topcell=<topcell>")
        self.add_klayout_drcparam("drc", "report=<report>")
        self.add_klayout_drcparam("drc", "threads=<threads>")

        with self.active_dataroot("root"):
            with self.active_fileset("klayout.drc"):
                self.add_file("interposer.drc", filetype="drc")
                self.add_runsetfileset("drc", "klayout", "drc")

            with self.active_fileset("klayout.techmap"):
                self.add_file("layers.lyp", filetype="display")
                self.add_displayfileset("klayout")
