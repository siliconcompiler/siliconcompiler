import graphviz
import pytest

import os.path

from unittest.mock import patch, MagicMock

from siliconcompiler.schema import NamedSchema, BaseSchema
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

    check = Test.from_manifest(name="test", cfg=schema.getdict())
    assert check.get_dep() == []
    module_map = {obj.name: obj for obj in schema.get_dep()}
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

    check = Test.from_manifest(name="test", cfg=schema.getdict())
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
