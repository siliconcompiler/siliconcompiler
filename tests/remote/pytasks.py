'''Task classes the remote tests run, in a module of their own: a runner process
started for a test imports a node's task by module name, and a test module
would bring pytest and every fixture with it.'''

from siliconcompiler.tool import PythonEnvironment
from siliconcompiler.tools.builtin.nop import NOPTask


class RunsPython(NOPTask):
    '''A task whose tool runs the user's Python: what makes a node one the
    job's packages are installed for.'''

    def task(self):
        return "runspython"

    def get_python_environment(self):
        return PythonEnvironment()


class AcmeTask(NOPTask):
    '''One tool's task with a dataroot of its own, `scripts`, from wherever
    ``SOURCE`` says: every task of the tool registers one of that name, from a
    source of its own (surface D298).'''

    SOURCE = None

    def __init__(self):
        super().__init__()
        self.set_dataroot("scripts", self.SOURCE, tag="v1")
        with self.active_dataroot("scripts"):
            self.set_refdir(f"tcl/{self.task()}")

    def tool(self):
        return "acme_sim"


class AcmeRun(AcmeTask):
    SOURCE = "https://github.com/siliconcompiler/acme-run/archive/refs/tags/"

    def task(self):
        return "run"


class AcmeCheck(AcmeTask):
    SOURCE = "https://github.com/siliconcompiler/acme-check/archive/refs/tags/"

    def task(self):
        return "check"
