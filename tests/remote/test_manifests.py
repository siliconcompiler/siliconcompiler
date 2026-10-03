import importlib
import os
import sys

import pytest

from siliconcompiler import Flowgraph, Project
from siliconcompiler.remote import manifests
from siliconcompiler.tools.builtin.nop import NOPTask


# Reading a manifest somebody else wrote: every class it names is looked up
# among the classes already loaded, and nothing is imported on its behalf.


@pytest.fixture
def unloaded(monkeypatch):
    '''A module on the path that has never been imported, and says so if it is.'''
    marker = "imported"
    with open("sc_not_yet_loaded.py", "w") as f:
        f.write(f"open({marker!r}, 'w').write('imported')\n"
                "from siliconcompiler import Project\n"
                "class NamedProject(Project):\n    pass\n")
    monkeypatch.syspath_prepend(".")
    monkeypatch.delitem(sys.modules, "sc_not_yet_loaded", raising=False)
    return marker


def imported(marker):
    return os.path.exists(marker)


def test_a_class_a_manifest_names_is_looked_up_and_not_imported(unloaded):
    cfg = Project().getdict()
    cfg["__meta__"]["class"] = "sc_not_yet_loaded/NamedProject"

    project = manifests.read(cfg=cfg)

    assert not imported(unloaded)
    assert type(project) is Project               # unknown: its base type


def test_a_class_already_loaded_resolves(unloaded):
    module = importlib.import_module("sc_not_yet_loaded")

    project = manifests.read(cfg=module.NamedProject().getdict())

    assert type(project) is module.NamedProject


def test_a_task_class_is_never_imported_by_reading(unloaded):
    '''Only its name is read, whole manifest and all; the caller checks it
    against the loaded classes before anything asks for the task.'''
    flow = Flowgraph("f")
    flow.node("known", NOPTask())
    flow.node("unknown", NOPTask())
    project = Project()
    project.set_flow(flow)
    cfg = project.getdict()
    cfg["flowgraph"]["f"]["unknown"]["0"]["taskmodule"]["node"]["*"]["*"]["value"] = \
        "sc_not_yet_loaded/NamedTask"

    read = manifests.read(cfg=cfg, lazyload=False)
    names = {node: read.get_flow().get_graph_node(node, "0").get_taskmodule()
             for node in ("known", "unknown")}

    assert not imported(unloaded)
    assert names["unknown"] == "sc_not_yet_loaded/NamedTask"
    known = manifests.known_classes()
    assert names["known"] in known
    assert names["unknown"] not in known


def test_a_manifest_is_read_from_disk_as_siliconcompiler_reads_it(unloaded):
    project = Project()
    project.write_manifest("in.pkg.json.gz")

    assert type(manifests.read("in.pkg.json.gz")) is Project
