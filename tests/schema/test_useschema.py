import graphviz
import pytest

import os.path

from unittest.mock import patch

from siliconcompiler.schema import UseSchema, NamedSchema, BaseSchema


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
    assert use.get_dependency("thisname") is dep


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
    assert use.get_dependency("thisname") is dep0
    assert use.use(dep1, clobber=True)
    assert use.get_dependency("thisname") is dep1


def test_use_no_clobber():
    use = UseSchema()

    dep0 = NamedSchema("thisname")
    dep1 = NamedSchema("thisname")
    assert use.use(dep0)
    assert use.get_dependency("thisname") is dep0
    assert use.use(dep1, clobber=False) is False
    assert use.get_dependency("thisname") is dep0


def test_get_dependency_not_found():
    use = UseSchema()

    with pytest.raises(KeyError, match="notthere is not an imported dependency"):
        use.get_dependency("notthere")


def test_remove_dependency_not_there():
    use = UseSchema()
    assert use.remove_dependency("notthere") is False


def test_remove_dependency():
    use = UseSchema()
    use.use(NamedSchema("thisname"))
    assert use.get_dependency("thisname")
    assert use.remove_dependency("thisname") is True
    assert use.get_all_dependencies() == []


def test_get_all_dependencies_empty():
    assert UseSchema().get_all_dependencies() == []


def test_get_all_dependencies():
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

    assert use.get_all_dependencies() == [dep00, dep10, dep01, dep11]


def test_get_all_dependencies_no_hier():
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

    assert use.get_all_dependencies(hierarchy=False) == [dep00, dep01]


def test_get_all_dependencies_repeats():
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

    assert use.get_all_dependencies() == [dep00, dep10, dep11, dep01]


def test_get_all_dependencies_non_use():
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

    assert use.get_all_dependencies() == \
        [dep00, dep10, dep20, dep01, dep11, dep21]


def test_get_all_dependencies_circle():
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

    assert use.get_all_dependencies() == [dep00, dep10, dep01, dep11]


def test_write_dependencygraph_no_graphviz_exe():
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
            use.write_dependencygraph("test.png")
        render.assert_called_once()


def test_write_dependencygraph():
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

    use.write_dependencygraph("test.png")
    assert os.path.exists("test.png")


def test_write_dependencygraph_alt_config():
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

    use.write_dependencygraph("test.png", landscape=True, border=False)
    assert os.path.exists("test.png")


def test_write_dependencygraph_repeats():
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

    use.write_dependencygraph("test.png")
    assert os.path.exists("test.png")


def test_write_dependencygraph_circle():
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

    use.write_dependencygraph("test.png")
    assert os.path.exists("test.png")
