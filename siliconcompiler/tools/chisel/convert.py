import os
import shutil
import glob

import os.path

from siliconcompiler import sc_open

from siliconcompiler import Task


class ConvertTask(Task):
    def __init__(self):
        super().__init__()

        self.add_parameter("application", "str", "Application name of the chisel program")
        self.add_parameter("argument", "[str]", "Arguments for the chisel build")
        self.add_parameter("targetdir", "str", "Output target directory name",
                           defvalue="chisel-output")

    def tool(self):
        return "chisel"

    def task(self):
        return "convert"

    def parse_version(self, stdout):
        # sbt version in this project: 1.5.5
        # sbt script version: 1.5.5

        for line in stdout.splitlines():
            line = line.strip()
            if 'sbt script version:' in line:
                return line.split()[-1]
            if 'sbt runner version:' in line:
                return line.split()[-1]

        return None

    def setup(self):
        super().setup()

        self.set_exe("sbt", vswitch="--version")
        self.add_version(">=1.5.5")

        self.set_threads(1)

        self.set_dataroot("chisel-tool", __file__)
        with self.active_dataroot("chisel-tool"):
            self.set_refdir("template")

        self.add_output_file(ext="v")

        self.add_required_key("option", "design")
        self.add_required_key("option", "fileset")
        if self.project.get("option", "alias"):
            self.add_required_key("option", "alias")

        # Mark required
        for lib, fileset in self.project.get_filesets():
            if lib.has_file(fileset=fileset, filetype="chisel"):
                self.add_required_key(lib, "fileset", fileset, "file", "chisel")
            elif lib.has_file(fileset=fileset, filetype="scala"):
                self.add_required_key(lib, "fileset", fileset, "file", "scala")

        if self.get("var", "application"):
            self.add_required_key("var", "application")
        if self.get("var", "argument"):
            self.add_required_key("var", "argument")
        self.add_required_key("var", "targetdir")

    def pre_process(self):
        super().pre_process()
        refdir = self.find_files('refdir')[0]

        chisel = None
        for lib, fileset in self.project.get_filesets():
            if lib.get_file(fileset=fileset, filetype="chisel"):
                chisel = lib.get_file(fileset=fileset, filetype="chisel")
            if chisel:
                break
        if chisel:
            chisel = chisel[0]

        if chisel:
            build_dir = os.path.dirname(chisel)
            # Expect file tree from: https://www.scala-sbt.org/1.x/docs/Directories.html
            # copy build.sbt
            # copy src/
            shutil.copyfile(chisel, os.path.join(self.nodeworkdir, 'build.sbt'))
            shutil.copytree(os.path.join(build_dir, 'src'),
                            os.path.join(self.nodeworkdir, 'src'))
            if os.path.exists(os.path.join(build_dir, 'project')):
                shutil.copytree(os.path.join(build_dir, 'project'),
                                os.path.join(self.nodeworkdir, 'project'))
            return

        for filename in ('build.sbt', 'SCDriver.scala'):
            src = os.path.join(refdir, filename)
            dst = filename
            shutil.copyfile(src, dst)

        # Chisel driver relies on Scala files being collected into '$CWD/inputs'
        for lib, fileset in self.project.get_filesets():
            if lib.get_file(fileset=fileset, filetype="scala"):
                for file in lib.get_file(fileset=fileset, filetype="scala"):
                    shutil.copy2(file, "inputs/")

    def runtime_options(self):
        options = super().runtime_options()
        options.append('-batch')
        options.append('--no-share')
        options.append('--no-global')

        run_main = ["runMain"]

        chisel = None
        for lib, fileset in self.project.get_filesets():
            if lib.get_file(fileset=fileset, filetype="chisel"):
                chisel = lib.get_file(fileset=fileset, filetype="chisel")
            if chisel:
                break
        if chisel:
            chisel = chisel[0]

        if chisel:
            app = self.design_topmodule
            if self.get("var", "application"):
                app = self.get("var", "application")

            run_main.append(app)
            run_main.extend(self.get("var", "argument"))

            run_main.append("--")

            run_main.extend(["--target-dir", self.get("var", "targetdir")])
        else:
            # Use built in driver
            run_main.append("SCDriver")
            run_main.extend(["--module", self.design_topmodule])

            run_main.extend(["--output-file", f"../outputs/{self.design_topmodule}.v"])

        options.append(" ".join(run_main))

        return options

    def post_process(self):
        super().post_process()

        chisel_path = self.get("var", "targetdir")
        if os.path.exists(chisel_path):
            with open(f'outputs/{self.design_topmodule}.v', 'w') as out:
                for f in glob.glob(os.path.join(chisel_path, '*.v')):
                    with sc_open(f) as i_file:
                        out.writelines(i_file.readlines())
