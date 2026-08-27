'''
SODA-OPT is the MLIR front end of PNNL's SODA Synthesizer, an end-to-end path
from a high-level machine learning framework down to accelerator RTL.

It takes a bufferized MLIR module -- typically what a PyTorch, TensorFlow or
TFLite model lowers to through TOSA and linalg -- and performs the
hardware/software split: the compute of interest is marked, outlined into a
kernel function, optimized for high-level synthesis, and lowered to the LLVM
dialect so that an HLS tool can turn it into Verilog. In SiliconCompiler that
HLS tool is :ref:`Bambu <tool-bambu>`, and the Verilog it emits feeds the normal
ASIC or FPGA flow.

soda-opt is an out-of-tree MLIR project linked against MLIR's C++ libraries, so
it has to be built against the same llvm-project revision as the
:ref:`MLIR tools <tool-mlir>` it runs beside.

Documentation: https://gitlab.pnnl.gov/sodalite/soda-opt

Sources: https://github.com/pnnl/soda-opt

Installation: ``sc-install soda`` (run ``sc-install mlir`` first)
'''

import os

import os.path

from typing import List, Optional, Tuple

from siliconcompiler import Task
from siliconcompiler.utils import sc_open


class SODATask(Task):
    '''Common behavior for the soda-opt command line tools.

    soda-opt is built on MLIR's ``mlir-opt`` driver, so it shares that family's
    ``--version`` format and its file-in/file-out shape: a task either continues
    a chain of MLIR nodes or starts one from the design's filesets.

    This deliberately does not inherit from
    :class:`~siliconcompiler.tools.mlir.MLIRTask`. The two resemble each other
    because both wrap an LLVM command line tool, not because a soda task is an
    mlir one -- they report different tools, are installed by different scripts,
    and version independently. Sharing a base would make ``isinstance(task,
    MLIRTask)`` true for something that runs ``soda-opt``, and would couple two
    tool drivers that are meant to be droppable on their own.
    '''

    def tool(self) -> str:
        return "soda"

    def parse_version(self, stdout: str) -> str:
        # LLVM (http://llvm.org/):
        #   LLVM version 19.1.5
        #   Optimized build.
        #   Default target: x86_64-unknown-linux-gnu
        #
        # An out-of-tree tool built against MLIR reports the version of the
        # llvm-project it was built from, which is the number that matters:
        # the MLIR pass names and dialects are versioned with it, and soda-opt
        # has no version of its own to report.
        for line in stdout.splitlines():
            line = line.strip()
            if line.startswith("LLVM version"):
                return line.split()[-1]
        return None

    def _input_from_upstream(self, ext: str) -> bool:
        '''Reports whether an upstream node supplies this task's input.

        Both :meth:`_setup_input` and :meth:`_get_input` decide off this, so a
        node that is fed by the flow never silently falls back to the design's
        filesets when the staging did not happen -- which for a chain of MLIR
        nodes would mean re-reading the original source and quietly dropping
        every transformation before it.

        Args:
            ext (str): Extension of the file produced by an upstream node.
        '''
        return f"{self.design_topmodule}.{ext}" in self.get_files_from_input_nodes()

    def _setup_input(self, ext: str, filetype: str) -> None:
        '''Declares this task's input, which is either an upstream node's output
        or, for the first node of a chain, a file from the design's filesets.

        Args:
            ext (str): Extension of the file produced by an upstream node.
            filetype (str): SiliconCompiler filetype to look for in the filesets.
        '''
        if self._input_from_upstream(ext):
            self.add_input_file(ext=ext)
            return

        self.add_required_key("option", "design")
        self.add_required_key("option", "fileset")
        if self.project.get("option", "alias"):
            self.add_required_key("option", "alias")

        for lib, fileset in self.project.get_filesets():
            if lib.has_file(fileset=fileset, filetype=filetype):
                self.add_required_key(lib, "fileset", fileset, "file", filetype)

    def _get_input(self, ext: str, filetype: str) -> str:
        '''Returns the path of the file this task reads, resolved the same way
        :meth:`_setup_input` declared it.

        Args:
            ext (str): Extension of the file produced by an upstream node.
            filetype (str): SiliconCompiler filetype to look for in the filesets.

        Raises:
            ValueError: If neither an upstream node nor a fileset supplies one.
        '''
        if self._input_from_upstream(ext):
            return os.path.join("inputs", f"{self.design_topmodule}.{ext}")

        for lib, fileset in self.project.get_filesets():
            files = lib.get_file(fileset=fileset, filetype=filetype)
            if files:
                if len(files) > 1:
                    raise ValueError(
                        f"{self.tool()}/{self.task()} takes a single {filetype} file, "
                        f"got {len(files)}: {', '.join(files)}")
                return files[0]

        raise ValueError(
            f"{self.tool()}/{self.task()} has no input: no upstream node produced "
            f"{self.design_topmodule}.{ext} and no fileset provides a {filetype} file")

    def _record_output_lines(self, path: str) -> Optional[int]:
        '''Counts the lines of a module this task wrote and records them as a metric.

        The size of the module a node hands downstream is the cheapest signal of
        what its passes did to it -- an outlined and unrolled kernel is visibly
        bigger than the module it came from -- so the task reports it. The
        argument-description files it writes alongside the module are not
        modules and are not counted.

        This is duplicated from :class:`~siliconcompiler.tools.mlir.MLIRTask`
        rather than shared, for the reason the class docstring above gives: the
        two task families are deliberately unrelated types, which is also why
        :func:`render_pipeline_options` exists in both modules.

        Args:
            path (str): Path to the file, relative to the node's work directory.

        Returns:
            int: The number of lines counted, or None if the file is not there.
        '''
        # post_process() runs whether or not the tool succeeded, so the file a
        # failed node never wrote has to be tolerated: a metric is worth nothing
        # next to the real error, and raising here would bury it under a
        # traceback. The scheduler checks the declared outputs either way.
        if not os.path.exists(path):
            return None

        with sc_open(path) as f:
            # wc -l counts newlines, so a file whose last line is unterminated
            # comes up one short. That line is still a line the downstream node
            # reads, so iterating over the file counts it.
            lines = sum(1 for _ in f)

        # There is no lines metric in the schema, so record_metric() drops the
        # value; quiet keeps it from warning about that on every run of every
        # node, and the number starts landing the day a metric is added.
        self.record_metric("lines", lines, path, quiet=True)

        return lines


def render_pipeline_options(options: List[Tuple[str, Optional[object]]]) -> str:
    '''Renders soda-opt pass-pipeline options into the ``flag a=1 b=2`` form the
    MLIR ``PassPipelineOptions`` parser expects.

    A value of None drops the option, so a caller can build the list without
    branching on every knob, and a value of True emits the bare flag, which the
    parser reads as true.

    Args:
        options (list of (str, object)): Option name/value pairs.

    Returns:
        str: The rendered option string, empty if nothing was set.
    '''
    rendered = []
    for name, value in options:
        if value is None:
            continue
        if value is True:
            rendered.append(name)
        else:
            rendered.append(f"{name}={value}")
    return " ".join(rendered)
