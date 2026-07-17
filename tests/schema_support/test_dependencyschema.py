import graphviz
import pytest

import copy
import json
import os.path

from unittest.mock import patch, MagicMock

from siliconcompiler import Design, Project
from siliconcompiler.schema import NamedSchema, BaseSchema
from siliconcompiler.schema.parameter import Parameter
from siliconcompiler.schema_support.dependencyschema import DependencySchema
from siliconcompiler.schema_support.pathschema import PathSchemaSimpleBase, PathSchema


def test_init():
    schema = DependencySchema()
    assert schema.getkeys() == ("deps",)
    assert schema.get("deps") == []


def test_add_dep_invalid():
    schema = DependencySchema()

    with pytest.raises(TypeError,
                       match=r"^Cannot add an object of type: <class "
                       r"'siliconcompiler\.schema\.baseschema\.BaseSchema'>$"):
        schema.add_dep(BaseSchema())


def test_add_dep():
    schema = DependencySchema()

    dep = NamedSchema("thisname")
    assert schema.add_dep(dep)
    assert schema.get_dep("thisname") is dep
    assert schema.get("deps") == ["thisname"]
    assert schema.get("deps", field="lock") is True


def test_has_dep():
    schema = DependencySchema()

    assert schema.has_dep("thisname") is False
    assert schema.add_dep(NamedSchema("thisname"))
    assert schema.has_dep("thisname") is True


def test_has_dep_with_object():
    schema = DependencySchema()

    dep = NamedSchema("thisname")
    assert schema.has_dep("thisname") is False
    assert schema.add_dep(dep)
    assert schema.has_dep(dep) is True


def test_has_dep_invalid():
    schema = DependencySchema()

    assert schema.has_dep(1) is False
    assert schema.has_dep(BaseSchema()) is False
    assert schema.has_dep(NamedSchema) is False


def test_add_dep_clobber():
    schema = DependencySchema()

    dep0 = NamedSchema("thisname")
    dep1 = NamedSchema("thisname")
    assert schema.add_dep(dep0)
    assert schema.get_dep("thisname") is dep0
    assert schema.add_dep(dep1, clobber=True)
    assert schema.get_dep("thisname") is dep1
    assert schema.get("deps") == ["thisname"]


def test_add_dep_no_clobber():
    schema = DependencySchema()

    dep0 = NamedSchema("thisname")
    dep1 = NamedSchema("thisname")
    assert schema.add_dep(dep0)
    assert schema.get_dep("thisname") is dep0
    assert schema.add_dep(dep1, clobber=False) is False
    assert schema.get_dep("thisname") is dep0
    assert schema.get("deps") == ["thisname"]


def test_add_dep_unnamed():
    schema = DependencySchema()

    with pytest.raises(ValueError, match=r"^Cannot add an unnamed dependency$"):
        schema.add_dep(NamedSchema())


def test_get_dep_not_found():
    schema = DependencySchema()

    with pytest.raises(KeyError, match=r"^'notthere is not an imported module'$"):
        schema.get_dep("notthere")


def test_remove_dep_not_there():
    schema = DependencySchema()
    assert schema.remove_dep("notthere") is False


def test_remove_dep():
    schema = DependencySchema()
    schema.add_dep(NamedSchema("thisname"))
    assert schema.get_dep("thisname")
    assert schema.remove_dep("thisname") is True
    assert schema.get("deps", field="lock") is True
    assert schema.get_dep() == []
    assert schema.get("deps") == []


def test_remove_dep_with_object():
    schema = DependencySchema()
    dep = NamedSchema("thisname")
    schema.add_dep(dep)
    assert schema.get_dep("thisname")
    assert schema.remove_dep(dep) is True
    assert schema.get("deps", field="lock") is True
    assert schema.get_dep() == []
    assert schema.get("deps") == []


def test_remove_dep_multiple():
    schema = DependencySchema()
    dep_a = NamedSchema("a")
    dep_b = NamedSchema("b")
    dep_c = NamedSchema("c")
    schema.add_dep(dep_a)
    schema.add_dep(dep_b)
    schema.add_dep(dep_c)

    assert schema.get("deps") == ["a", "b", "c"]

    # Removing one dependency leaves the others intact and ordered.
    assert schema.remove_dep("b") is True
    assert schema.has_dep("b") is False
    assert schema.get("deps") == ["a", "c"]
    assert schema.get_dep() == [dep_a, dep_c]
    assert schema.get("deps", field="lock") is True


def test_get_dep_empty():
    assert DependencySchema().get_dep() == []


def test_get_dep():
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            super().__init__()
            self.set_name(name)

    schema = DependencySchema()

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.add_dep(dep10)
    assert dep01.add_dep(dep11)

    assert schema.add_dep(dep00)
    assert schema.add_dep(dep01)

    assert schema.get_dep() == [dep00, dep10, dep01, dep11]


def test_get_dep_no_hier():
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            super().__init__()
            self.set_name(name)

    schema = DependencySchema()

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.add_dep(dep10)
    assert dep01.add_dep(dep11)

    assert schema.add_dep(dep00)
    assert schema.add_dep(dep01)

    assert schema.get_dep(hierarchy=False) == [dep00, dep01]


def test_get_dep_repeats():
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            super().__init__()
            self.set_name(name)

    schema = DependencySchema()

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.add_dep(dep10)
    assert dep00.add_dep(dep11)
    assert dep01.add_dep(dep11)

    assert schema.add_dep(dep00)
    assert schema.add_dep(dep01)

    assert schema.get_dep() == [dep00, dep10, dep11, dep01]


def test_get_dep_non_dep():
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            super().__init__()
            self.set_name(name)

    schema = DependencySchema()

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")
    dep20 = NamedSchema("level2-0")
    dep21 = NamedSchema("level2-1")

    assert dep00.add_dep(dep10)
    assert dep10.add_dep(dep20)
    assert dep01.add_dep(dep11)
    assert dep11.add_dep(dep21)

    assert schema.add_dep(dep00)
    assert schema.add_dep(dep01)

    assert schema.get_dep() == \
        [dep00, dep10, dep20, dep01, dep11, dep21]


def test_get_dep_hier():
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            super().__init__()
            self.set_name(name)

    schema = DependencySchema()

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep02 = Test("level0-2")

    assert dep00.add_dep(dep01)
    assert dep01.add_dep(dep02)

    assert schema.add_dep(dep00)

    assert schema.get_dep("level0-0") is dep00
    assert schema.get_dep("level0-0").get_dep("level0-1") is dep01
    assert schema.get_dep("level0-0").get_dep("level0-1").get_dep("level0-2") is dep02


def test_get_dep_circle():
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            super().__init__()
            self.set_name(name)

    schema = DependencySchema()

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.add_dep(dep10)
    assert dep10.add_dep(dep01)
    assert dep01.add_dep(dep11)
    assert dep11.add_dep(dep00)

    assert schema.add_dep(dep00)

    assert schema.get_dep() == [dep00, dep10, dep01, dep11]


@pytest.mark.skip(reason="cyclic dependency graphs cannot yet be serialized "
                         "into a self-contained manifest (see finding A); "
                         "revisit once dependency serialization is reworked")
def test_getdict_with_cycle():
    # A cyclic dependency graph is permitted by add_dep (see test_get_dep_circle)
    # but the nested manifest embedding recurses indefinitely on a cycle. Once
    # dependency serialization preserves graph identity (canonical name table),
    # this should produce a finite, reloadable manifest instead of recursing.
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            super().__init__()
            self.set_name(name)

    dep0 = Test("dep0")
    dep1 = Test("dep1")
    assert dep0.add_dep(dep1)
    assert dep1.add_dep(dep0)

    cfg = dep0.getdict()

    reload = Test.from_manifest(name="dep0", cfg=cfg)
    assert sorted(d.name for d in reload.get_dep()) == ["dep0", "dep1"]


def test_write_depgraph_no_graphviz_exe():
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            super().__init__()
            self.set_name(name)

    schema = Test("top")

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.add_dep(dep10)
    assert dep01.add_dep(dep11)

    assert schema.add_dep(dep00)
    assert schema.add_dep(dep01)

    with patch("graphviz.Digraph.render") as render:
        def raise_error(*args, **kwargs):
            raise graphviz.ExecutableNotFound("args")
        render.side_effect = raise_error

        with pytest.raises(RuntimeError,
                           match=r"^Unable to save flowgraph: failed to execute 'a', make sure the "
                                 r"Graphviz executables are on your systems' PATH$"):
            schema.write_depgraph("test.png")
        render.assert_called_once()


def test_write_depgraph(has_graphviz):
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            super().__init__()
            self.set_name(name)

    schema = Test("top")

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.add_dep(dep10)
    assert dep01.add_dep(dep11)

    assert schema.add_dep(dep00)
    assert schema.add_dep(dep01)

    schema.write_depgraph("test.png")
    assert os.path.exists("test.png")


def test_write_depgraph_alt_config(has_graphviz):
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            super().__init__()
            self.set_name(name)

    schema = Test("top")

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.add_dep(dep10)
    assert dep01.add_dep(dep11)

    assert schema.add_dep(dep00)
    assert schema.add_dep(dep01)

    schema.write_depgraph("test.png", landscape=True, border=False)
    assert os.path.exists("test.png")


def test_write_depgraph_repeats(has_graphviz):
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            super().__init__()
            self.set_name(name)

    schema = Test("top")

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.add_dep(dep10)
    assert dep00.add_dep(dep11)
    assert dep01.add_dep(dep11)

    assert schema.add_dep(dep00)
    assert schema.add_dep(dep01)

    schema.write_depgraph("test.png")
    assert os.path.exists("test.png")


def test_write_depgraph_circle(has_graphviz):
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            super().__init__()
            self.set_name(name)

    schema = Test("top")

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.add_dep(dep10)
    assert dep10.add_dep(dep01)
    assert dep01.add_dep(dep11)
    assert dep11.add_dep(dep00)

    assert schema.add_dep(dep00)

    schema.write_depgraph("test.png")
    assert os.path.exists("test.png")


def test_populate_deps_empty():
    schema = DependencySchema()
    schema._populate_deps({})


def test_populate_deps_missing_meta():
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name=None):
            super().__init__()
            self.set_name(name)

    schema = Test("top")

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.add_dep(dep10)
    assert dep01.add_dep(dep11)

    assert schema.add_dep(dep00)
    assert schema.add_dep(dep01)

    cfg = schema.getdict()
    del cfg['__meta__']['__deps__']
    check = Test.from_manifest(name="test", cfg=cfg)
    assert check.get_dep() == []
    module_map = {obj.name: obj for obj in schema.get_dep()}
    check._populate_deps(module_map)
    assert check.get_dep() == schema.get_dep()


def test_populate_deps():
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name=None):
            super().__init__()
            self.set_name(name)

    schema = Test("top")

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.add_dep(dep10)
    assert dep01.add_dep(dep11)

    assert schema.add_dep(dep00)
    assert schema.add_dep(dep01)

    cfg = schema.getdict()
    check = Test.from_manifest(name="test", cfg=cfg)
    assert sorted([dep.name for dep in check.get_dep(hierarchy=False)]) == ["level0-0", "level0-1"]


def test_from_dict_with_version():
    # from_manifest does not expose the version argument, so _from_dict is
    # driven directly to exercise the branch that injects the schema version
    # into each dependency's manifest before it is loaded.
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name=None):
            super().__init__()
            self.set_name(name)

    schema = Test("top")

    dep00 = Test("level0-0")
    dep10 = Test("level1-0")

    assert dep00.add_dep(dep10)
    assert schema.add_dep(dep00)

    cfg = schema.getdict()

    seen_cfgs = []
    orig_from_manifest = NamedSchema.from_manifest.__func__

    def spy(cls, *args, cfg=None, **kwargs):
        # snapshot before loading mutates the dict in place
        seen_cfgs.append(copy.deepcopy(cfg))
        return orig_from_manifest(cls, *args, cfg=cfg, **kwargs)

    check = Test("top")
    with patch.object(NamedSchema, "from_manifest", classmethod(spy)):
        check._from_dict(cfg, tuple(), version=(1, 2, 3))

    # The version path still populates the dependencies correctly.
    assert [dep.name for dep in check.get_dep(hierarchy=False)] == ["level0-0"]

    # Each dependency manifest had the schema version injected before loading.
    # Round-trip the injected field through Parameter so a malformed cfg would
    # surface here rather than being silently accepted.
    assert seen_cfgs
    for depcfg in seen_cfgs:
        assert BaseSchema._version_key in depcfg
        param = Parameter.from_dict(depcfg[BaseSchema._version_key],
                                    (BaseSchema._version_key,),
                                    None)
        assert param.get() == "1.2.3"


def test_populate_deps_reset():
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name=None):
            super().__init__()
            self.set_name(name)

    schema = Test("top")

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.add_dep(dep10)
    assert dep01.add_dep(dep11)

    assert schema.add_dep(dep00)
    assert schema.add_dep(dep01)

    cfg = schema.getdict()
    check = Test.from_manifest(name="test", cfg=cfg)
    assert sorted([dep.name for dep in check.get_dep(hierarchy=False)]) == ["level0-0", "level0-1"]
    module_map = {obj.name: obj for obj in schema.get_dep()}
    check._reset_deps()
    check._populate_deps(module_map)
    assert check.get_dep() == schema.get_dep()


def test_populate_deps_missing():
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name=None):
            super().__init__()
            self.set_name(name)

    schema = Test("top")

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.add_dep(dep10)
    assert dep01.add_dep(dep11)

    assert schema.add_dep(dep00)
    assert schema.add_dep(dep01)

    cfg = schema.getdict()
    del cfg['__meta__']['__deps__']
    check = Test.from_manifest(name="test", cfg=cfg)
    with pytest.raises(ValueError, match=r"^level0-0 not available in map$"):
        check._populate_deps({})


def test_populate_deps_already_populated():
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            super().__init__()
            self.set_name(name)

    schema = Test("top")

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep10 = Test("level1-0")
    dep11 = Test("level1-1")

    assert dep00.add_dep(dep10)
    assert dep01.add_dep(dep11)

    assert schema.add_dep(dep00)
    assert schema.add_dep(dep01)

    check = Test("top")
    check.add_dep(dep00)

    assert check.get_dep() == [dep00, dep10]
    module_map = {obj.name: obj for obj in schema.get_dep()}
    check._populate_deps(module_map)
    assert check.get_dep() == [dep00, dep10]


def test_populate_deps_recursive():
    # Exercises the recursive branch of _populate_deps: a dependency that is
    # itself an unpopulated DependencySchema must have its own deps resolved.
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            super().__init__()
            self.set_name(name)

    top = Test("top")
    mid = Test("mid")
    leaf = Test("leaf")

    assert mid.add_dep(leaf)
    assert top.add_dep(mid)

    # Clear the resolved object maps while leaving the "deps" name lists intact,
    # so _populate_deps has to rebuild the hierarchy from the module map.
    top._reset_deps()
    mid._reset_deps()

    assert top.get_dep(hierarchy=False) == []
    assert mid.get_dep(hierarchy=False) == []

    module_map = {"mid": mid, "leaf": leaf}
    top._populate_deps(module_map)

    # Direct dep resolved on top, and the nested dep resolved recursively on mid.
    assert top.get_dep(hierarchy=False) == [mid]
    assert mid.get_dep(hierarchy=False) == [leaf]
    assert top.get_dep() == [mid, leaf]


def test_check_filepaths_none():
    assert DependencySchema().check_filepaths() is True


@pytest.mark.parametrize("pcls", (PathSchemaSimpleBase, PathSchema))
def test_check_filepaths_self(pcls):
    class Test(DependencySchema, pcls):
        pass

    with patch("siliconcompiler.schema_support.pathschema.PathSchemaBase.check_filepaths") as cf:
        cf.return_value = True
        assert Test().check_filepaths() is True
        cf.assert_called_once()


@pytest.mark.parametrize("pcls", (PathSchemaSimpleBase, PathSchema))
def test_check_filepaths_self_fail(pcls):
    class Test(DependencySchema, pcls):
        pass

    with patch("siliconcompiler.schema_support.pathschema.PathSchemaBase.check_filepaths") as cf:
        cf.return_value = False
        assert Test().check_filepaths() is False
        cf.assert_called_once()


def test_check_filepaths_skips_non_pathschema_dep():
    class Test(DependencySchema, PathSchema):
        pass

    dut = Test()
    # A dependency that is not a PathSchemaBase must be skipped, not checked.
    dut.add_dep(NamedSchema("plaindep"))

    with patch("siliconcompiler.schema_support.pathschema.PathSchemaBase.check_filepaths") as cf:
        cf.return_value = True
        assert dut.check_filepaths() is True
        # Only self is checked; the plain NamedSchema dependency is skipped.
        cf.assert_called_once()


def test_check_filepaths_ignore_keys_forwarded():
    class Test(NamedSchema, DependencySchema, PathSchema):
        def __init__(self, name=None):
            super().__init__()
            self.set_name(name)

    dut = Test("top")
    dut.add_dep(Test("dep0"))

    ignore = [("key", "path")]
    with patch("siliconcompiler.schema_support.pathschema.PathSchemaBase.check_filepaths") as cf:
        cf.return_value = True
        assert dut.check_filepaths(ignore_keys=ignore) is True
        assert cf.call_count == 2
        # ignore_keys is forwarded to every checked object (self and deps).
        for call in cf.call_args_list:
            assert call.kwargs["ignore_keys"] is ignore


def test_check_filepaths_depth_fail():
    class Test(DependencySchema, PathSchema):
        pass

    class TestDepth(NamedSchema, DependencySchema, PathSchema):
        pass

    dut = Test()
    dep = TestDepth("testdepth0")
    dep.add_dep(TestDepth("testdepth1"))
    dut.add_dep(dep)

    with patch("siliconcompiler.schema_support.pathschema.PathSchemaBase.check_filepaths") as cf:
        cf.return_value = False
        assert dut.check_filepaths() is False
        assert cf.call_count == 3


def test_check_filepaths_depth_pass():
    class Test(DependencySchema, PathSchema):
        pass

    class TestDepth(NamedSchema, DependencySchema, PathSchema):
        pass

    dut = Test()
    dep = TestDepth("testdepth0")
    dep.add_dep(TestDepth("testdepth1"))
    dut.add_dep(dep)

    with patch("siliconcompiler.schema_support.pathschema.PathSchemaBase.check_filepaths") as cf:
        cf.return_value = True
        assert dut.check_filepaths() is True
        assert cf.call_count == 3


def test_check_filepaths_depth_partial():
    class Test(DependencySchema, PathSchema):
        pass

    class TestDepth(NamedSchema, DependencySchema, PathSchema):
        pass

    dut = Test()
    dep = TestDepth("testdepth0")
    dep.add_dep(TestDepth("testdepth1"))
    dut.add_dep(dep)

    def cf_call(obj, ignore_keys=None):
        try:
            if obj.name == "testdepth1":
                return False
        except:  # noqa E722
            pass
        return True

    with patch("siliconcompiler.schema_support.pathschema.PathSchemaBase.check_filepaths") as cf:
        cf.side_effect = cf_call
        assert dut.check_filepaths() is False
        assert cf.call_count == 3


# ── _write_depgraph static method ────────────────────────────────────────────


def _capture_dot(filename, root, graph, **kwargs):
    """Run _write_depgraph with a mocked graphviz.Digraph; return the mock."""
    dot = MagicMock()
    dot.graph_attr = {}
    with patch("graphviz.Digraph", return_value=dot):
        DependencySchema._write_depgraph(filename, root, graph, **kwargs)
    return dot


def _node_calls(dot):
    """Return dict mapping node id → kwargs from dot.node call_args_list."""
    return {c.args[0]: c.kwargs for c in dot.node.call_args_list}


def _edge_pairs(dot):
    """Return set of (src, dst) tuples from dot.edge call_args_list."""
    return {(c.args[0], c.args[1]) for c in dot.edge.call_args_list}


def test_write_depgraph_static_empty_graph():
    dot = _capture_dot("test.png", "root", {})
    dot.node.assert_not_called()
    dot.edge.assert_not_called()
    dot.render.assert_called_once()


def test_write_depgraph_static_single_node():
    dot = _capture_dot("test.png", "root", {"root": set()})
    assert len(_node_calls(dot)) == 1
    assert "root" in _node_calls(dot)


def test_write_depgraph_static_root_default_box():
    dot = _capture_dot("test.png", "root", {"root": set()})
    assert _node_calls(dot)["root"]["shape"] == "box"


def test_write_depgraph_static_non_root_default_oval():
    dot = _capture_dot("test.png", "root", {"root": {"child"}, "child": set()})
    assert _node_calls(dot)["child"]["shape"] == "oval"


def test_write_depgraph_static_text_defaults_to_node_id():
    dot = _capture_dot("test.png", "root", {"root": set()})
    assert _node_calls(dot)["root"]["label"] == "root"


def test_write_depgraph_static_node_style_shape_override():
    dot = _capture_dot("test.png", "root", {"root": set()},
                       node_styles={"root": {"shape": "diamond"}})
    assert _node_calls(dot)["root"]["shape"] == "diamond"


def test_write_depgraph_static_node_style_text_override():
    dot = _capture_dot("test.png", "root", {"root": set()},
                       node_styles={"root": {"text": "My Label"}})
    assert _node_calls(dot)["root"]["label"] == "My Label"


def test_write_depgraph_static_node_style_color_override():
    dot = _capture_dot("test.png", "root", {"root": set()},
                       node_styles={"root": {"color": "#ff0000"}})
    assert _node_calls(dot)["root"]["fillcolor"] == "#ff0000"


def test_write_depgraph_static_color_defaults_to_background():
    dot = _capture_dot("test.png", "root", {"root": set()}, background="#123456")
    assert _node_calls(dot)["root"]["fillcolor"] == "#123456"


def test_write_depgraph_static_edges_created():
    dot = _capture_dot("test.png", "root",
                       {"root": {"a", "b"}, "a": set(), "b": set()})
    pairs = _edge_pairs(dot)
    assert ("root", "a") in pairs
    assert ("root", "b") in pairs


def test_write_depgraph_static_no_edges_without_connections():
    dot = _capture_dot("test.png", "root", {"root": set(), "orphan": set()})
    dot.edge.assert_not_called()


def test_write_depgraph_static_landscape():
    dot = _capture_dot("test.png", "root", {}, landscape=True)
    assert dot.graph_attr["rankdir"] == "LR"


def test_write_depgraph_static_portrait():
    dot = _capture_dot("test.png", "root", {}, landscape=False)
    assert dot.graph_attr["rankdir"] == "TB"


def test_write_depgraph_static_border_off():
    dot = _capture_dot("test.png", "root", {"root": set()}, border=False)
    assert _node_calls(dot)["root"]["penwidth"] == "0"


def test_write_depgraph_static_border_on():
    dot = _capture_dot("test.png", "root", {"root": set()}, border=True)
    assert _node_calls(dot)["root"]["penwidth"] == "1"


def test_write_depgraph_static_no_graphviz_exe():
    dot = MagicMock()
    dot.graph_attr = {}
    dot.render.side_effect = graphviz.ExecutableNotFound("missing")
    with patch("graphviz.Digraph", return_value=dot):
        with pytest.raises(RuntimeError, match=r"^Unable to save flowgraph:"):
            DependencySchema._write_depgraph("test.png", "root", {})


def test_write_depgraph_static_node_styles_none_uses_defaults():
    dot = _capture_dot("test.png", "root", {"root": set()}, node_styles=None)
    assert _node_calls(dot)["root"]["shape"] == "box"


def test_write_depgraph_static_partial_node_styles():
    dot = _capture_dot("test.png", "root",
                       {"root": {"child"}, "child": set()},
                       node_styles={"root": {"text": "Root Node"}})
    calls = _node_calls(dot)
    assert calls["root"]["label"] == "Root Node"
    assert calls["child"]["label"] == "child"


# ── write_depgraph → _write_depgraph delegation ──────────────────────────────


class _TestDep(NamedSchema, DependencySchema):
    def __init__(self, name):
        super().__init__()
        self.set_name(name)


def test_write_depgraph_delegates_to_static():
    schema = _TestDep("top")
    schema.add_dep(_TestDep("dep0"))

    with patch.object(DependencySchema, "_write_depgraph") as mock_static:
        schema.write_depgraph("out.png")

    mock_static.assert_called_once()
    filename, root, _ = mock_static.call_args.args[:3]
    assert filename == "out.png"
    assert root == "top"


def test_write_depgraph_root_connects_to_direct_deps():
    schema = _TestDep("top")
    schema.add_dep(_TestDep("dep0"))
    schema.add_dep(_TestDep("dep1"))

    with patch.object(DependencySchema, "_write_depgraph") as mock_static:
        schema.write_depgraph("out.png")

    graph = mock_static.call_args.args[2]
    assert "lib-dep0" in graph["top"]
    assert "lib-dep1" in graph["top"]


def test_write_depgraph_dep_nodes_included_with_edges():
    dep0 = _TestDep("dep0")
    dep1 = _TestDep("dep1")
    dep0.add_dep(dep1)
    schema = _TestDep("top")
    schema.add_dep(dep0)

    with patch.object(DependencySchema, "_write_depgraph") as mock_static:
        schema.write_depgraph("out.png")

    graph = mock_static.call_args.args[2]
    assert "lib-dep0" in graph
    assert "lib-dep1" in graph["lib-dep0"]


def test_write_depgraph_leaf_dep_has_empty_edges():
    schema = _TestDep("top")
    schema.add_dep(_TestDep("dep0"))

    with patch.object(DependencySchema, "_write_depgraph") as mock_static:
        schema.write_depgraph("out.png")

    graph = mock_static.call_args.args[2]
    assert graph["lib-dep0"] == set()


def test_write_depgraph_root_styled_as_box():
    schema = _TestDep("top")

    with patch.object(DependencySchema, "_write_depgraph") as mock_static:
        schema.write_depgraph("out.png")

    node_styles = mock_static.call_args.kwargs["node_styles"]
    assert node_styles["top"]["shape"] == "box"


def test_write_depgraph_dep_styled_as_oval():
    schema = _TestDep("top")
    schema.add_dep(_TestDep("dep0"))

    with patch.object(DependencySchema, "_write_depgraph") as mock_static:
        schema.write_depgraph("out.png")

    node_styles = mock_static.call_args.kwargs["node_styles"]
    assert node_styles["lib-dep0"]["shape"] == "oval"


def test_write_depgraph_dep_label_is_original_name():
    schema = _TestDep("top")
    schema.add_dep(_TestDep("dep0"))

    with patch.object(DependencySchema, "_write_depgraph") as mock_static:
        schema.write_depgraph("out.png")

    node_styles = mock_static.call_args.kwargs["node_styles"]
    assert node_styles["lib-dep0"]["text"] == "dep0"


def test_write_depgraph_visual_params_forwarded():
    schema = _TestDep("top")

    with patch.object(DependencySchema, "_write_depgraph") as mock_static:
        schema.write_depgraph("out.png", fontcolor="#aabbcc", background="#001122",
                              fontsize="18", border=False, landscape=True)

    kw = mock_static.call_args.kwargs
    assert kw["fontcolor"] == "#aabbcc"
    assert kw["background"] == "#001122"
    assert kw["fontsize"] == "18"
    assert kw["border"] is False
    assert kw["landscape"] is True


def test_getdict_with_nodeps():
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            super().__init__()
            self.set_name(name)

    schema = DependencySchema()

    assert "__deps__" not in schema.getdict()['__meta__']


def test_getdict_with_deps():
    class Test(NamedSchema, DependencySchema):
        def __init__(self, name):
            super().__init__()
            self.set_name(name)

    schema = DependencySchema()

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep02 = Test("level0-2")

    assert dep00.add_dep(dep01)
    assert dep01.add_dep(dep02)

    assert schema.add_dep(dep00)

    cfg = schema.getdict()

    assert "__deps__" in cfg['__meta__']
    dpescfg = cfg['__meta__']["__deps__"]
    assert "level0-0" in dpescfg
    assert "level0-1" not in dpescfg
    assert "level0-1" in dpescfg["level0-0"]["__meta__"]["__deps__"]
    assert "level0-2" not in dpescfg
    assert "level0-2" in \
        dpescfg["level0-0"]["__meta__"]["__deps__"]["level0-1"]["__meta__"]["__deps__"]


def test_getdict_with_deps_project():
    class Test(Design):
        def __init__(self, name):
            super().__init__()
            self.set_name(name)

    schema = Test("top")

    dep00 = Test("level0-0")
    dep01 = Test("level0-1")
    dep02 = Test("level0-2")

    assert dep00.add_dep(dep01)
    assert dep01.add_dep(dep02)

    assert schema.add_dep(dep00)

    d = Design("test")
    d.add_dep(schema)

    Project(d)

    assert "__deps__" not in schema.getdict()['__meta__']


def test_write_manifest_self_contained_for_design_in_project(tmp_path):
    # A design imported into a project stores its deps centrally in the project,
    # so the project-owned manifest omits them. But writing that design's
    # manifest *directly* must still produce a self-contained file: the on-disk
    # manifest should embed the full, recursive dependency tree.
    #
    # This fails until write_manifest on a design that lives inside a project
    # emits its dependencies; today the deps are dropped.
    top = Design("top")
    child = Design("child")
    grandchild = Design("grandchild")

    assert child.add_dep(grandchild)
    assert top.add_dep(child)

    Project(top)
    assert isinstance(top._parent(root=True), Project)

    path = str(tmp_path / "top.json")
    top.write_manifest(path)

    with open(path) as fout:
        cfg = json.load(fout)

    deps = cfg["__meta__"].get("__deps__", {})
    assert "child" in deps
    assert "grandchild" in deps["child"]["__meta__"].get("__deps__", {})


def test_write_manifest_roundtrip_for_design_in_project(tmp_path):
    # The self-contained manifest of a design taken from a project must reload
    # on its own into a fully populated design hierarchy of the correct types.
    #
    # This fails until write_manifest on a design that lives inside a project
    # emits its dependencies; today the reloaded design has no deps.
    top = Design("top")
    child = Design("child")
    grandchild = Design("grandchild")

    assert child.add_dep(grandchild)
    assert top.add_dep(child)

    Project(top)

    path = str(tmp_path / "top.json")
    top.write_manifest(path)

    reload = NamedSchema.from_manifest(filepath=path)
    assert isinstance(reload, Design)
    assert reload.name == "top"
    assert [dep.name for dep in reload.get_dep(hierarchy=False)] == ["child"]

    reload_child = reload.get_dep("child")
    assert isinstance(reload_child, Design)
    assert [dep.name for dep in reload_child.get_dep(hierarchy=False)] == ["grandchild"]
