#!/usr/bin/env python3
# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.
"""The SODA Synthesizer front end, driven from SiliconCompiler.

``mm`` is a batched matrix multiply in the TOSA dialect --
``mm-no_weights`` model, which is what a stateless ``torch.matmul`` exports to.
This script takes it through the SODA path, each stage exposed as an
:ref:`smake <howto_smake>` target::

    smake elaborate     # MLIR to Verilog: soda-opt plus Bambu, nothing else
    smake syn           # ...and on through synthesis and timing
    smake asic          # ...and on to GDSII
    smake compare       # baseline against optimized, on area and timing
    smake unrolled      # the optimized strategy at a different unroll depth
    smake model         # regenerate mm.mlir from PyTorch (needs requirements.txt)
    smake check         # verify every referenced file resolves

``compare`` is the reason both strategies are here: ``baseline`` lowers the
kernel with no HLS-oriented optimization, ``optimized`` runs soda-opt's Bambu
pipeline over it first, and the difference between the two is what the SODA
papers report. soda-opt has a third strategy, ``transformed``, which rewrites the
kernel under a transform dialect schedule; it needs a schedule to be worth
running, so it is left to
:class:`~siliconcompiler.flows.sodaflow.SODATransformedElaborationFlow` rather
than shipped here with a schedule that does nothing.

Each strategy is a flow of its own, and every flow that elaborates a design
takes one as its ``frontend``, which is how the SODA front end reaches GDSII
without a backend of its own: everything downstream of Bambu -- which upstream
is an OpenROAD-flow-scripts ``config.mk`` -- is SiliconCompiler's own ASIC flow.

Requires: mlir, soda, bambu (elaborate); plus yosys, opensta (syn); plus
openroad, klayout (asic); freepdk45 (via lambdapdk)
"""

import os.path

from typing import Dict, Optional, Sequence

from siliconcompiler import ASIC, Design

from siliconcompiler.flows.synflow import SynthesisFlow
from siliconcompiler.flows.asicflow import SODAASICFlow
from siliconcompiler.flows.sodaflow import SODA_STRATEGIES

from siliconcompiler.targets import freepdk45_demo

from siliconcompiler.tools.bambu.convert import ConvertTask as BambuConvertTask
from siliconcompiler.tools.soda.opt import OptimizedTask


class SODADesign(Design):
    """The ``mm`` design: a TOSA model plus the constraints its kernel is built to.

    The topmodule is ``forward_kernel`` rather than ``mm`` because soda-opt
    outlines the kernel it finds into ``<function>_kernel``, and that outlined
    kernel is what Bambu synthesizes and what everything downstream sees.
    """

    def __init__(self):
        super().__init__()
        self.set_name("mm")

        self.set_dataroot("soda", __file__)

        with self.active_dataroot("soda"):
            # The model, in TOSA. `smake model` regenerates it. The fileset is
            # named for what it holds rather than "rtl"; nothing keys off the
            # name, and the front end looks for a .mlir file across all of them.
            with self.active_fileset("soda"):
                self.set_topmodule("forward_kernel")
                self.add_file("mm.mlir")

            # Read three times over a build: by Bambu as its high-level
            # synthesis target, then by synthesis, then by place-and-route.
            with self.active_fileset("sdc"):
                self.add_file("mm.sdc")


def _project() -> ASIC:
    """Builds the project every target here starts from.

    Returns:
        ASIC: A project with the design and the target in place, but no flow
        selected.
    """
    project = ASIC(SODADesign())
    project.add_fileset(["soda", "sdc"])

    freepdk45_demo(project)

    return project


def _configure(project: ASIC) -> None:
    """Configures the tasks of a flow that has already been set.

    Task settings are per task, so they are applied once the flow has put the
    tasks into the project -- which is also what makes them reachable by
    ``find_task`` from anywhere, without the flow having to pass them through.

    Args:
        project (ASIC): The project whose flow was just selected.
    """
    # Match the high-level synthesis settings the SODA flow uses: two memory
    # channels, and bambu's balanced multi-port preset.
    bambu = BambuConvertTask.find_task(project)
    bambu.set_bambu_memorychannels(2)
    bambu.set_bambu_experimentalsetup("BAMBU-BALANCED-MP")


def elaborate(strategy: str = "optimized", jobname: Optional[str] = None) -> ASIC:
    """Runs the MLIR front end only, stopping at Verilog.

    This is the part of the flow that is SODA: TOSA to linalg, kernel outlining
    and optimization in soda-opt, translation to LLVM IR, and high-level
    synthesis in Bambu. It is the fastest way to see what a strategy or a knob
    does to the generated RTL, and the strategy's flow is run on its own here
    rather than as some other flow's front end.

    Args:
        strategy (str): The soda-opt strategy to use.
        jobname (str, optional): The job name. Defaults to the strategy.

    Returns:
        ASIC: The completed project.
    """
    project = _project()
    project.set_flow(SODA_STRATEGIES[strategy]())
    _configure(project)

    project.option.set_jobname(jobname or f"elaborate-{strategy}")

    project.run()
    project.summary()
    return project


def syn(strategy: str = "optimized", jobname: Optional[str] = None) -> ASIC:
    """Runs the front end and then synthesis and static timing analysis.

    The strategy's flow is handed to the synthesis flow as its ``frontend``,
    which is all it takes for a front end the flow knows nothing about to feed
    the ordinary Yosys and OpenSTA steps.

    Args:
        strategy (str): The soda-opt strategy to use.
        jobname (str, optional): The job name. Defaults to the strategy.

    Returns:
        ASIC: The completed project.
    """
    project = _project()
    project.set_flow(SynthesisFlow(frontend=SODA_STRATEGIES[strategy]()))
    _configure(project)

    project.option.set_jobname(jobname or f"syn-{strategy}")

    project.run()
    project.summary()
    return project


def asic(strategy: str = "optimized", jobname: Optional[str] = None) -> ASIC:
    """Takes the model all the way to GDSII.

    Args:
        strategy (str): The soda-opt strategy to use.
        jobname (str, optional): The job name. Defaults to the strategy.

    Returns:
        ASIC: The completed project.
    """
    project = _project()
    project.set_flow(SODAASICFlow(strategy=strategy))
    _configure(project)

    project.option.set_jobname(jobname or f"asic-{strategy}")

    project.run()
    project.summary()
    project.snapshot()
    return project


def unrolled(unrolls: int = 3) -> ASIC:
    """Synthesizes the optimized strategy with a different unroll depth.

    Every stage of soda-opt's Bambu pipeline is a task setter, so a design can
    be swept over them without touching the flow. The number of full unrolls is
    the one that moves area and latency the most: each application unrolls one
    more level of the loop nest, trading cells for cycles.

    Args:
        unrolls (int): How many times the full-unroll pass is applied.

    Returns:
        ASIC: The completed project.
    """
    project = _project()
    project.set_flow(SynthesisFlow(frontend=SODA_STRATEGIES["optimized"]()))
    _configure(project)

    OptimizedTask.find_task(project).set_soda_fullunrolls(unrolls)

    project.option.set_jobname(f"unroll{unrolls}")

    project.run()
    project.summary()
    return project


def compare(strategies: Sequence[str] = ("baseline", "optimized")) -> Dict[str, dict]:
    """Synthesizes each strategy and reports what the optimization bought.

    Bambu's own estimate is recorded by the ``convert`` node and the mapped
    result by ``synthesis``, so the two sit side by side: how well the HLS
    tool predicted the hardware, and how much smaller or faster the optimized
    kernel actually is.

    Args:
        strategies (sequence of str): The strategies to compare.

    Returns:
        dict: Per strategy, the collected metrics.
    """
    results = {}
    for strategy in strategies:
        project = syn(strategy)
        history = project.history(f"syn-{strategy}")

        results[strategy] = {
            "hls cellarea": history.get("metric", "cellarea", step="convert", index="0"),
            "hls registers": history.get("metric", "registers", step="convert", index="0"),
            "hls fmax": history.get("metric", "fmax", step="convert", index="0"),
            "syn cellarea": history.get("metric", "cellarea", step="synthesis", index="0"),
            "syn cells": history.get("metric", "cells", step="synthesis", index="0"),
            "setupslack": history.get("metric", "setupslack", step="timing", index="0"),
        }

    columns = sorted({metric for values in results.values() for metric in values})
    width = max(len(column) for column in columns)

    print()
    print("soda-opt strategy comparison")
    print(f"{'metric':<{width}}  " + "  ".join(f"{s:>14}" for s in strategies))
    for column in columns:
        cells = []
        for strategy in strategies:
            value = results[strategy].get(column)
            cells.append(f"{'n/a':>14}" if value is None else f"{value:>14.4g}")
        print(f"{column:<{width}}  " + "  ".join(cells))
    print()

    return results


def model(output: Optional[str] = None) -> str:
    """Regenerates ``mm.mlir`` from the PyTorch model it came from.

    The MLIR is checked in so the flow can be built without a PyTorch install;
    this is here so it can be regenerated, and so the model it describes is not
    only a comment.

    Needs torch and torch-mlir, neither of which SiliconCompiler depends on:
    ``pip install -r requirements.txt`` in this directory.

    Args:
        output (str, optional): Where to write the MLIR. Defaults to the
            checked-in ``mm.mlir``.

    Returns:
        str: The path written.
    """
    import torch
    from torch_mlir import torchscript

    class MM(torch.nn.Module):
        """A stateless batched matrix multiply: no weights, just the two inputs."""

        def forward(self, input1, input2):
            return torch.matmul(input1, input2)

    if output is None:
        output = os.path.join(os.path.dirname(__file__), "mm.mlir")

    # [bs, M, K] x [bs, K, N]. Small enough that the optimized strategy can
    # fully unroll it, which is what makes the comparison interesting.
    input1 = torch.randn(1, 4, 8)
    input2 = torch.randn(1, 8, 4)

    module = torchscript.compile(MM(), (input1, input2),
                                 output_type="tosa", use_tracing=True)
    with open(output, "w", encoding="utf-8") as f:
        f.write(str(module))

    return output


def check():
    """Checks that every file the design references resolves."""
    assert SODADesign().check_filepaths()


if __name__ == "__main__":
    # Elaboration is the cheapest target that exercises the whole SODA front
    # end, so it is what a bare run does.
    elaborate()
