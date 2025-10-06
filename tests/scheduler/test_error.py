import pytest
import sys

from siliconcompiler.scheduler import SCRuntimeError


def test_msg():
    exception = SCRuntimeError("msg")
    assert exception.args == ('msg',)
    assert exception.msg == "msg"


@pytest.mark.skipif(sys.version_info < (3, 10), reason="error changed between 3.9 and 3.10")
def test_require_arg():
    with pytest.raises(TypeError,
                       match=r"^SCRuntimeError\.__init__\(\) missing 1 required positional "
                             r"argument: 'msg'$"):
        SCRuntimeError()
