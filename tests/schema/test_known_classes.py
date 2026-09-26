import pytest

from siliconcompiler import Flowgraph
from siliconcompiler.schema import BaseSchema
from siliconcompiler.schema.baseschema import known_classes_only
from siliconcompiler.tools.builtin.nop import NOPTask


# Reading a manifest somebody else wrote: every class it names is looked up
# among the classes already loaded, and nothing is imported on its behalf.


@pytest.fixture
def unloaded(tmp_path, monkeypatch):
    '''A module on the path that has never been imported, and says so if it is.'''
    marker = tmp_path / "imported"
    (tmp_path / "sc_not_yet_loaded.py").write_text(
        f"open({str(marker)!r}, 'w').write('imported')\n"
        "from siliconcompiler.schema import BaseSchema\n"
        "from siliconcompiler.tools.builtin.nop import NOPTask\n"
        "class Named(BaseSchema):\n    pass\n"
        "class NamedTask(NOPTask):\n    pass\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    return marker


def test_a_class_a_manifest_names_is_looked_up_and_not_imported(unloaded):
    manifest = BaseSchema().getdict()
    manifest["__meta__"] = {"class": "sc_not_yet_loaded/Named"}

    with known_classes_only():
        schema = BaseSchema.from_manifest(cfg=manifest)

    assert not unloaded.exists()
    assert type(schema) is BaseSchema             # unknown: its base, as ever


def test_a_class_already_loaded_resolves(unloaded):
    class Loaded(BaseSchema):
        pass

    manifest = Loaded().getdict()

    with known_classes_only():
        assert type(BaseSchema.from_manifest(cfg=manifest)) is Loaded


def test_a_task_module_is_looked_up_and_an_unknown_one_raises(unloaded):
    flow = Flowgraph("f")
    flow.node("known", NOPTask())
    flow.node("unknown", NOPTask())
    flow.get_graph_node("unknown", "0").set("taskmodule", "sc_not_yet_loaded/NamedTask")

    with known_classes_only():
        assert flow.get_task_module("known", "0") is NOPTask
        with pytest.raises(ImportError, match="not a task class"):
            flow.get_task_module("unknown", "0")

    assert not unloaded.exists()


def test_outside_the_context_nothing_changes(unloaded):
    '''The restriction is the reader's to ask for; everything else imports as
    it always has.'''
    manifest = BaseSchema().getdict()
    manifest["__meta__"] = {"class": "sc_not_yet_loaded/Named"}

    assert BaseSchema._known_classes() is None
    assert type(BaseSchema.from_manifest(cfg=manifest)).__name__ == "Named"
    assert unloaded.exists()
