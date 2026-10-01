import pytest

import os.path

import siliconcompiler

from siliconcompiler.tools.chisel import convert
from siliconcompiler.tools.gtkwave import show
from siliconcompiler.tools.klayout import export
from siliconcompiler.tools.magic import drc
from siliconcompiler.tools.netgen import lvs
from siliconcompiler.tools.openroad import global_placement, init_floorplan
from siliconcompiler.tools.opensta import timing
from siliconcompiler.tools.vivado import syn_fpga
from siliconcompiler.tools.yosys import syn_asic


@pytest.mark.parametrize("task_cls,dataroot,directory", [
    (convert.ConvertTask, "chisel-tool", "chisel"),
    (show.ShowTask, "gtkwave", "gtkwave"),
    (export.ExportTask, "refdir", "klayout"),
    (drc.DRCTask, "magic", "magic"),
    (lvs.LVSTask, "netgen", "netgen"),
    (global_placement.GlobalPlacementTask, "openroad-ref", "openroad"),
    (init_floorplan.InitFloorplanTask, "sc-common", "_common"),
    (timing.TimingTask, "refdir-root", "opensta"),
    (syn_fpga.SynthesisTask, "vivado", "vivado"),
    (syn_asic.ASICSynthesis, "siliconcompiler-yosys", "yosys"),
    (syn_asic.ASICSynthesis, "yosys-techmaps", "yosys"),
])
def test_driver_dataroot_names_installed_package(task_cls, dataroot, directory):
    # A driver's own files are named through the installed package, not by
    # where its module sits on this machine, and resolve as they did by path.
    task = task_cls.make_docs()

    assert task.get("dataroot", dataroot, "path") == \
        f"python://siliconcompiler/tools/{directory}"
    assert task.get_dataroot(dataroot) == \
        os.path.join(os.path.dirname(siliconcompiler.__file__), "tools", directory)
    for key in ("refdir", "script"):
        if task.get(key, step="<step>", index="<index>"):
            assert all(os.path.exists(path)
                       for path in task.find_files(key, step="<step>", index="<index>"))
