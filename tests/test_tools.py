import pytest

from siliconcompiler.project import Project
from siliconcompiler import Task, Design
from siliconcompiler.schema import EditableSchema
from siliconcompiler.tool import ToolSchema
from siliconcompiler.tools import get_task


@pytest.mark.parametrize("arg", [None, Design(), "string"])
def test_get_task_notproject(arg):
    with pytest.raises(TypeError, match="project must be a Project"):
        get_task(arg)


def test_get_task():
    class FauxTask(Task):
        def tool(self):
            return "faux"

    class FauxTask0(FauxTask):
        def task(self):
            return "task0"

    class FauxTask1(FauxTask):
        def task(self):
            return "task1"

    class FauxTask2(Task):
        def tool(self):
            return "anotherfaux"

        def task(self):
            return "task1"

    faux0 = FauxTask0()
    faux1 = FauxTask1()
    faux2 = FauxTask2()

    proj = Project()
    EditableSchema(proj).insert("tool", "faux", ToolSchema())
    EditableSchema(proj).insert("tool", "faux", "task", "task0", faux0)
    EditableSchema(proj).insert("tool", "faux", "task", "task1", faux1)
    EditableSchema(proj).insert("tool", "anotherfaux", ToolSchema())
    EditableSchema(proj).insert("tool", "anotherfaux", "task", "task1", faux2)

    assert get_task(proj) == set([faux0, faux1, faux2])
    assert get_task(proj, tool="faux") == set([faux0, faux1])
    assert get_task(proj, task="task1") == set([faux1, faux2])
    assert get_task(proj, tool="faux", task="task1") is faux1
    assert get_task(proj, filter=lambda t: isinstance(t, FauxTask)) == set([faux0, faux1])
    assert get_task(proj, filter=lambda t: isinstance(t, FauxTask2)) is faux2
    assert get_task(proj, filter=FauxTask2) is faux2


def test_get_task_missing():
    assert get_task(Project(), "tool0", "task0") == set()


def test_get_task_empty():
    assert get_task(Project()) == set()
