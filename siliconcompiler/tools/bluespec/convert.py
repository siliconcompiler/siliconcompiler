import os
import shutil

import os.path

from siliconcompiler import sc_open

from siliconcompiler import Task


class ConvertTask(Task):
    VLOGDIR = "verilog"
    BSCDIR = "bluespec"

    def tool(self):
        return "bluespec"

    def task(self):
        return "convert"

    def parse_version(self, stdout):
        # Examples:
        # Bluespec Compiler, version 2021.12.1-27-g9a7d5e05 (build 9a7d5e05)
        # Bluespec Compiler, version 2021.07 (build 4cac6eba)

        long_version = stdout.split()[3]
        return long_version.split('-')[0]

    def setup(self):
        super().setup()

        self.set_exe("bsc", vswitch="-v")
        self.add_version(">=2021.07")

        self.set_threads(1)

        self.add_output_file(ext="v")
        self.add_output_file(ext="dot")

        self.add_required_key("option", "design")
        self.add_required_key("option", "fileset")
        if self.project.get("option", "alias"):
            self.add_required_key("option", "alias")

        # Mark required
        for lib, fileset in self.project.get_filesets():
            if lib.has_idir(fileset):
                self.add_required_key(lib, "fileset", fileset, "idir")
            if lib.get("fileset", fileset, "define"):
                self.add_required_key(lib, "fileset", fileset, "define")
            if lib.has_file(fileset=fileset, filetype="bsv"):
                self.add_required_key(lib, "fileset", fileset, "file", "bsv")

    def pre_process(self):
        super().pre_process()
        # bsc requires its output directory exists before being called.
        for path in (ConvertTask.VLOGDIR, ConvertTask.BSCDIR):
            if os.path.isdir(path):
                shutil.rmtree(path)
            os.makedirs(path)

    def runtime_options(self):
        options = super().runtime_options()

        options.append('-verilog')
        options.extend(['-vdir', ConvertTask.VLOGDIR])
        options.extend(['-bdir', ConvertTask.BSCDIR])
        options.extend(['-info-dir', 'reports'])
        options.append('-u')
        options.append('-v')

        options.append('-show-module-use')
        options.append('-sched-dot')

        options.extend(['-g', self.design_topmodule])

        filesets = self.project.get_filesets()
        idirs = []
        defines = []
        for lib, fileset in filesets:
            idirs.extend(lib.get_idir(fileset))
            defines.extend(lib.get("fileset", fileset, "define"))

        bsc_path = ':'.join(idirs + ['%/Libraries'])
        options.extend(['-p', bsc_path])

        for value in idirs:
            options.extend(['-I', value])
        for value in defines:
            options.extend(['-D', value])

        sources = []
        for lib, fileset in filesets:
            if lib.get_file(fileset=fileset, filetype="bsv"):
                for value in lib.get_file(fileset=fileset, filetype="bsv"):
                    sources.append(value)
        if len(sources) != 1:
            raise ValueError('Bluespec only supports one source file!')
        options.extend(sources)

        return options

    def post_process(self):
        super().post_process()

        shutil.copyfile(f"reports/{self.design_topmodule}_combined_full.dot",
                        f"outputs/{self.design_topmodule}.dot")

        extra_modules = set()
        use_file = os.path.join(ConvertTask.VLOGDIR, f"{self.design_topmodule}.use")
        if os.path.exists(use_file):
            bsc_tool_path = os.path.dirname(
                os.path.dirname(
                    self.schema_record.get('toolpath', step=self.step, index=self.index)))
            bsc_lib = os.path.join(bsc_tool_path, "lib", "Verilog")

            with sc_open(use_file) as f:
                for module in f:
                    module = module.strip()
                    mod_path = os.path.join(bsc_lib, f"{module}.v")
                    if os.path.exists(mod_path):
                        extra_modules.add(mod_path)
                    else:
                        self.logger.warning(f"Unable to find module {module} source "
                                            f"files at: {bsc_lib}")

        # bsc outputs each compiled module to its own Verilog file, so we
        # concatenate them all to create a pickled output we can pass along.
        with open(os.path.join('outputs', f'{self.design_topmodule}.v'), 'w') as pickled_vlog:
            for src in os.listdir(ConvertTask.VLOGDIR):
                if src.endswith(".v"):
                    with sc_open(os.path.join(ConvertTask.VLOGDIR, src)) as vlog_mod:
                        pickled_vlog.write(vlog_mod.read())

            pickled_vlog.write("\n")
            pickled_vlog.write("// Bluespec imports\n\n")
            for vfile in extra_modules:
                with sc_open(os.path.join(bsc_lib, vfile)) as vlog_mod:
                    pickled_vlog.write(vlog_mod.read() + "\n")
