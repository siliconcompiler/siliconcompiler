import pytest

from siliconcompiler.scheduler import SCRuntimeError


def test_msg():
    exception = SCRuntimeError("msg")
    assert exception.args == ('msg',)
    assert exception.msg == "msg"


def test_require_arg():
    with pytest.raises(TypeError,
                       match=r"^SCRuntimeError\.__init__\(\) missing 1 required positional "
                             r"argument: 'msg'$"):
        SCRuntimeError()
