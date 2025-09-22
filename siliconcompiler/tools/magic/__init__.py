'''
Magic is a chip layout viewer, editor, and circuit verifier with
built in DRC and LVS engines.

Documentation: http://opencircuitdesign.com/magic/userguide.html

Installation: https://github.com/RTimothyEdwards/magic

Sources: https://github.com/RTimothyEdwards/magic
'''

import gzip
import shutil

import os.path

from siliconcompiler.schema.parametervalue import PathNodeValue
from siliconcompiler import Task


class MagicTask(Task):
    def __init__(self):
        super().__init__()

        self.add_parameter("read_lef", "[file]", "lef files to read")

    def tool(self):
        return "magic"

    def parse_version(self, stdout):
        return stdout.strip('\n')

    def setup(self):
        super().setup()

        self.set_exe("magic", vswitch="--version", format="tcl")
        self.add_version(">=8.3.196")

        self.set_threads()

        self.set_dataroot("magic", __file__)
        with self.active_dataroot("magic"):
            self.set_refdir("scripts")
        self.set_script("sc_magic.tcl")

        self.add_commandline_option("-noc")
        self.add_commandline_option("-dnull")

        if f"{self.design_topmodule}.gds" in self.get_files_from_input_nodes():
            self.add_input_file(ext="gds")
        else:
            for lib, fileset in self.project.get_filesets():
                if lib.has_file(fileset=fileset, filetype="gds"):
                    self.add_required_key(lib, "fileset", fileset, "file", "gds")

        self.add_regex("errors", r'^Error')
        self.add_regex("warnings", r'warning')

        if self.get("var", "read_lef"):
            self.add_required_key("var", "read_lef")
        self.add_required_key("asic", "pdk")

    def pre_process(self):
        super().pre_process()
        # pdk = chip.get('option', 'pdk')
        # stackup = chip.get('option', 'stackup')
        # mainlib = get_mainlib(chip)
        # libtype = chip.get('library', mainlib, 'asic', 'libarch', step=step, index=index)
        # process_file('lef', chip, 'pdk', pdk, 'aprtech', 'magic', stackup, libtype, 'lef')

        # for lib in get_libraries(chip, 'logic'):
        #     process_file('lef', chip, 'library', lib, 'output', stackup, 'lef')

        # for lib in get_libraries(chip, 'macro'):
        #     if lib in chip.get('tool', tool, 'task', task, 'var', 'exclude', step=step,
        # index=index):
        #         process_file('lef', chip, 'library', lib, 'output', stackup, 'lef')

    def _add_read_lef(self, path):
        if path.lower().endswith('.gz'):
            new_file_name = f'inputs/sc_{PathNodeValue.generate_hashed_path(path[:-3], None)}'

            with gzip.open(path, 'rt', encoding="utf-8") as fin:
                with open(new_file_name, 'w') as fout:
                    fout.write(fin.read().encode("ascii", "ignore").decode("ascii"))
        else:
            new_file_name = f'inputs/sc_{PathNodeValue.generate_hashed_path(path, None)}'
            shutil.copy2(path, new_file_name)

        self.add("var", "read_lef", os.path.abspath(new_file_name))
