import os
import shutil
import glob

import os.path

from typing import Dict, Optional, List, Union

from siliconcompiler import sc_open

from siliconcompiler import Task


class ConvertTask(Task):
    def __init__(self):
        super().__init__()

        self.add_parameter("application", "str", "Application name of the chisel program")
        self.add_parameter("argument", "[str]", "Arguments for the chisel build")
        self.add_parameter("targetdir", "str", "Output target directory name",
                           defvalue="chisel-output")

    def set_chisel_application(self, application: str,
                               step: Optional[str] = None, index: Optional[str] = None) -> None:
        """
        Sets the application name of the chisel program.

        Args:
            application (str): The application name.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "application", application, step=step, index=index)

    def add_chisel_argument(self, argument: Union[str, List[str]],
                            step: Optional[str] = None, index: Optional[str] = None,
                            clobber: bool = False) -> None:
        """
        Adds arguments for the chisel build.

        Args:
            argument (Union[str, List[str]]): The argument(s) to add.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
            clobber (bool, optional): If True, overwrites the existing list. Defaults to False.
        """
        if clobber:
            self.set("var", "argument", argument, step=step, index=index)
        else:
            self.add("var", "argument", argument, step=step, index=index)

    def set_chisel_targetdir(self, targetdir: str,
                             step: Optional[str] = None,
                             index: Optional[str] = None) -> None:
        """
        Sets the output target directory name.

        Args:
            targetdir (str): The target directory name.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "targetdir", targetdir, step=step, index=index)

    def tool(self):
        return "chisel"

    def task(self):
        return "convert"

    def get_runtime_environmental_variables(self, include_path: bool = True) \
            -> Dict[str, str]:
        envvars = super().get_runtime_environmental_variables(include_path=include_path)

        # sbt fetches its own launcher and every jar the build depends on through
        # coursier, and it does so on each run: the node working directory is
        # emptied before the tool starts, and --no-share (see runtime_options)
        # puts sbt's boot and ivy directories inside it. Coursier's cache is the
        # one part that would survive, and only because it defaults to
        # ~/.cache/coursier -- outside [option,cachedir], so nothing
        # SiliconCompiler manages ever sees it, and not among the volumes mounted
        # into a task container, so a containerised run re-resolves from nothing
        # every time. Re-resolving is not merely slow: Maven Central answers a
        # busy CI with HTTP 429 and the node fails for reasons that have nothing
        # to do with the design. Coursier prunes its own cache, so as with the
        # ccache tools there is nothing here to create and nothing to collect.
        #
        # Anyone who has already said where their coursier cache goes keeps it,
        # whether that is [option,env] / the task's own env or the ambient
        # environment. An empty value is not one of those: it names no directory,
        # so coursier falls back to its own default. Neither is a value equal to
        # the one this would set -- the node exports these variables into its own
        # environment before asking again, to write the replay script, so testing
        # for mere presence would by then be answering about this method's own
        # previous return and the replay script would go out without it. The
        # CCache mixin in tools/_common makes the same three checks for the same
        # reasons; change one and look at the other.
        toolcache = self.cachedir
        preset = envvars.get("COURSIER_CACHE", os.environ.get("COURSIER_CACHE"))
        if not preset or preset == toolcache:
            envvars["COURSIER_CACHE"] = toolcache

        return envvars

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

        # sbt 2.x runs through its native thin client by default, which leaves a
        # server JVM in the background after the build finishes -- keyed on this
        # node's working directory, which the next run replaces. --server puts
        # sbt in the foreground instead, so the node's processes end with the
        # node. sbt 1.x already worked this way, and has accepted the flag since
        # 1.4, so it is a no-op there.
        options.append('--server')

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
