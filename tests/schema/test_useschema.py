import graphviz
import pytest

import os.path

from unittest.mock import patch

from siliconcompiler.schema import UseSchema, NamedSchema, BaseSchema


def test_init():
    use = UseSchema()
    assert use.getkeys() == tuple(["used"])
    assert use.get("used") == []


def test_use_invalid():
    use = UseSchema()

    with pytest.raises(TypeError,
                       match="Cannot use an object of type: <class "
                       "'siliconcompiler.schema.baseschema.BaseSchema'>"):
        use.use(BaseSchema())


def test_use():
    use = UseSchema()

    dep = NamedSchema("thisname")
    assert use.use(dep)
    assert use.get_used("thisname") is dep
    assert use.get("used") == ["thisname"]


def test_use_confirm_reset():
    class Test(NamedSchema):
        def __init__(self):
            super().__init__("thisname")
            self.state_info = "notthis"

        def _reset(self):
            super()._reset()
            self.state_info = None

    use = UseSchema()

    dep = Test()
    assert dep.state_info == "notthis"
    assert use.use(dep)
    assert dep.state_info is None


def test_use_clobber():
    use = UseSchema()

    dep0 = NamedSchema("thisname")
    dep1 = NamedSchema("thisname")
    assert use.use(dep0)
    assert use.get_used("thisname") is dep0
    assert use.use(dep1, clobber=True)
    assert use.get_used("thisname") is dep1
    assert use.get("used") == ["thisname"]


def test_use_no_clobber():
    use = UseSchema()

    dep0 = NamedSchema("thisname")
    dep1 = NamedSchema("thisname")
    assert use.use(dep0)
    assert use.get_used("thisname") is dep0
    assert use.use(dep1, clobber=False) is False
    assert use.get_used("thisname") is dep0
    assert use.get("used") == ["thisname"]


def test_get_used_not_found():
    use = UseSchema()

    with pytest.raises(KeyError, match="notthere is not an imported module"):
        use.get_used("notthere")


def test_remove_use_not_there():
    use = UseSchema()
    assert use.remove_use("notthere") is False


def test_remove_use():
    use = UseSchema()
    use.use(NamedSchema("thisname"))
    assert use.get_used("thisname")
    assert use.remove_use("thisname") is True
    assert use.get_used() == []
    assert use.get("used") == []


def test_get_used_empty():
    assert UseSchema().get_used() == []


def test_get_used():
    class Test(NamedSchema, UseSchema):
        def __init__(self, name):
            NamedSchema.__init__(self, name)
            UseSchema.__init__(self)

    use = UseSchema()

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.use(dep10)
    assert dep01.use(dep11)

    assert use.use(dep00)
    assert use.use(dep01)

    assert use.get_used() == [dep00, dep10, dep01, dep11]


def test_get_used_no_hier():
    class Test(NamedSchema, UseSchema):
        def __init__(self, name):
            NamedSchema.__init__(self, name)
            UseSchema.__init__(self)

    use = UseSchema()

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.use(dep10)
    assert dep01.use(dep11)

    assert use.use(dep00)
    assert use.use(dep01)

    assert use.get_used(hierarchy=False) == [dep00, dep01]


def test_get_used_repeats():
    class Test(NamedSchema, UseSchema):
        def __init__(self, name):
            NamedSchema.__init__(self, name)
            UseSchema.__init__(self)

    use = UseSchema()

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.use(dep10)
    assert dep00.use(dep11)
    assert dep01.use(dep11)

    assert use.use(dep00)
    assert use.use(dep01)

    assert use.get_used() == [dep00, dep10, dep11, dep01]


def test_get_used_non_use():
    class Test(NamedSchema, UseSchema):
        def __init__(self, name):
            NamedSchema.__init__(self, name)
            UseSchema.__init__(self)

    use = UseSchema()

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")
    dep20 = NamedSchema("level2-0")
    dep21 = NamedSchema("level2-1")

    assert dep00.use(dep10)
    assert dep10.use(dep20)
    assert dep01.use(dep11)
    assert dep11.use(dep21)

    assert use.use(dep00)
    assert use.use(dep01)

    assert use.get_used() == \
        [dep00, dep10, dep20, dep01, dep11, dep21]


def test_get_used_circle():
    class Test(NamedSchema, UseSchema):
        def __init__(self, name):
            NamedSchema.__init__(self, name)
            UseSchema.__init__(self)

    use = UseSchema()

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.use(dep10)
    assert dep10.use(dep01)
    assert dep01.use(dep11)
    assert dep11.use(dep00)

    assert use.use(dep00)

    assert use.get_used() == [dep00, dep10, dep01, dep11]


def test_write_usegraph_no_graphviz_exe():
    class Test(NamedSchema, UseSchema):
        def __init__(self, name):
            NamedSchema.__init__(self, name)
            UseSchema.__init__(self)

    use = Test("top")

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.use(dep10)
    assert dep01.use(dep11)

    assert use.use(dep00)
    assert use.use(dep01)

    with patch("graphviz.Digraph.render") as render:
        def raise_error(*args, **kwargs):
            raise graphviz.ExecutableNotFound("args")
        render.side_effect = raise_error

        with pytest.raises(RuntimeError, match="Unable to save flowgraph: failed to execute"):
            use.write_usegraph("test.png")
        render.assert_called_once()


def test_write_usegraph():
    class Test(NamedSchema, UseSchema):
        def __init__(self, name):
            NamedSchema.__init__(self, name)
            UseSchema.__init__(self)

    use = Test("top")

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.use(dep10)
    assert dep01.use(dep11)

    assert use.use(dep00)
    assert use.use(dep01)

    use.write_usegraph("test.png")
    assert os.path.exists("test.png")


def test_write_usegraph_alt_config():
    class Test(NamedSchema, UseSchema):
        def __init__(self, name):
            NamedSchema.__init__(self, name)
            UseSchema.__init__(self)

    use = Test("top")

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.use(dep10)
    assert dep01.use(dep11)

    assert use.use(dep00)
    assert use.use(dep01)

    use.write_usegraph("test.png", landscape=True, border=False)
    assert os.path.exists("test.png")


def test_write_usegraph_repeats():
    class Test(NamedSchema, UseSchema):
        def __init__(self, name):
            NamedSchema.__init__(self, name)
            UseSchema.__init__(self)

    use = Test("top")

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.use(dep10)
    assert dep00.use(dep11)
    assert dep01.use(dep11)

    assert use.use(dep00)
    assert use.use(dep01)

    use.write_usegraph("test.png")
    assert os.path.exists("test.png")


def test_write_usegraph_circle():
    class Test(NamedSchema, UseSchema):
        def __init__(self, name):
            NamedSchema.__init__(self, name)
            UseSchema.__init__(self)

    use = Test("top")

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.use(dep10)
    assert dep10.use(dep01)
    assert dep01.use(dep11)
    assert dep11.use(dep00)

    assert use.use(dep00)

    use.write_usegraph("test.png")
    assert os.path.exists("test.png")


def test_populate_used_empty():
    use = UseSchema()
    use._populate_used({})


def test_populate_used():
    class Test(NamedSchema, UseSchema):
        def __init__(self, name):
            NamedSchema.__init__(self, name)
            UseSchema.__init__(self)

    use = Test("top")

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.use(dep10)
    assert dep01.use(dep11)

    assert use.use(dep00)
    assert use.use(dep01)

    check = Test.from_manifest("test", cfg=use.getdict())
    assert check.get_used() == []
    module_map = {obj.name(): obj for obj in use.get_used()}
    check._populate_used(module_map)
    assert check.get_used() == use.get_used()


def test_populate_used_missing():
    class Test(NamedSchema, UseSchema):
        def __init__(self, name):
            NamedSchema.__init__(self, name)
            UseSchema.__init__(self)

    use = Test("top")

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.use(dep10)
    assert dep01.use(dep11)

    assert use.use(dep00)
    assert use.use(dep01)

    check = Test.from_manifest("test", cfg=use.getdict())
    with pytest.raises(ValueError, match="level0-0 not available in map"):
        check._populate_used({})


def test_populate_used_already_populated():
    class Test(NamedSchema, UseSchema):
        def __init__(self, name):
            NamedSchema.__init__(self, name)
            UseSchema.__init__(self)

    use = Test("top")

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.use(dep10)
    assert dep01.use(dep11)

    assert use.use(dep00)
    assert use.use(dep01)

    check = Test("top")
    check.use(dep00)

    assert check.get_used() == [dep00, dep10]
    module_map = {obj.name(): obj for obj in use.get_used()}
    check._populate_used(module_map)
    assert check.get_used() == [dep00, dep10]
