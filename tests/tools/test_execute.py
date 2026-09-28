from siliconcompiler.tools.execute.exec_input import ExecInputTask


def test_tool_name():
    assert ExecInputTask().tool() == "execute"


def test_task_name():
    assert ExecInputTask().task() == "exec_input"


def test_remote_toolname_is_none():
    assert ExecInputTask()._remote_toolname is None


def test_remote_inherits_env_is_true():
    assert ExecInputTask()._remote_inherits_env is True
