import pytest

from siliconcompiler import Project, Task, Design
from siliconcompiler.schema import EditableSchema
from siliconcompiler.tools import get_task


# The module-level get_task() helper under test is deprecated in favor of
# Task.find_task(); every test here exercises that deprecated path deliberately
# and asserts the DeprecationWarning fires.
def _deprecated():
    return pytest.warns(DeprecationWarning, match="use cls.find_task instead")


@pytest.mark.parametrize("arg", [None, Design(), "string"])
def test_get_task_notproject(arg):
    with _deprecated(), pytest.raises(TypeError, match=r"^project must be a Project$"):
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
    EditableSchema(proj).insert("tool", "faux", "task", "task0", faux0)
    EditableSchema(proj).insert("tool", "faux", "task", "task1", faux1)
    EditableSchema(proj).insert("tool", "anotherfaux", "task", "task1", faux2)

    with _deprecated():
        assert get_task(proj) == set([faux0, faux1, faux2])
    with _deprecated():
        assert get_task(proj, tool="faux") == set([faux0, faux1])
    with _deprecated():
        assert get_task(proj, task="task1") == set([faux1, faux2])
    with _deprecated():
        assert get_task(proj, tool="faux", task="task1") is faux1
    with _deprecated():
        assert get_task(proj, filter=lambda t: isinstance(t, FauxTask)) == set([faux0, faux1])
    with _deprecated():
        assert get_task(proj, filter=lambda t: isinstance(t, FauxTask2)) is faux2
    with _deprecated():
        assert get_task(proj, filter=FauxTask2) is faux2

    with _deprecated(), pytest.raises(TypeError, match=r"^filter is not a recognized type$"):
        get_task(proj, filter=12)


def test_get_task_missing_filter_func():
    def thisfunc(*args):
        return False
    with _deprecated(), \
            pytest.raises(ValueError, match=r"^No tasks found matching filter=thisfunc$"):
        get_task(Project(), filter=thisfunc)


def test_get_task_missing_filter_lambda():
    with _deprecated(), \
            pytest.raises(ValueError, match=r"^No tasks found matching filter=<lambda>$"):
        get_task(Project(), filter=lambda _: False)


def test_get_task_missing_class():
    class FauxTask(Task):
        def tool(self):
            return "faux"

    with _deprecated(), \
            pytest.raises(ValueError,
                          match=r"^No tasks found matching tool='faux', class=FauxTask$"):
        get_task(Project(), filter=FauxTask)


def test_get_task_missing():
    with _deprecated(), \
            pytest.raises(ValueError,
                          match=r"^No tasks found matching tool='tool0', task='task0'$"):
        get_task(Project(), "tool0", "task0")


def test_get_task_empty():
    with _deprecated(), \
            pytest.raises(ValueError, match=r"^No tasks found matching any criteria$"):
        get_task(Project())
