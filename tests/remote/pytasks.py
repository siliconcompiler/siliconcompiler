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
