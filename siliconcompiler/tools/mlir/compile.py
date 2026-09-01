import os.path

from typing import Optional, Union

from pathlib import Path

from siliconcompiler.utils import sc_open

from siliconcompiler.tools.mlir import MLIRTask


class RuntimeTask(MLIRTask):
    '''Compiles a C support module into LLVM IR for linking into a kernel.

    Bufferized MLIR lowers ``memref.copy`` to a call to ``memrefCopy``, which
    upstream expects to come from MLIR's runner support library. An HLS backend
    has no runtime to link against, so the definition has to be merged into the
    module itself; this task produces it, and
    :class:`~siliconcompiler.tools.mlir.link.LinkTask` does the merge.

    The bundled ``memref_copy.c`` is the default, but the source is a parameter:
    any C file whose LLVM IR should end up inside the kernel goes here, and the
    module it produces is named after it.

    The task has no design input -- it compiles a source of its own -- so it is
    an entry node of any flow that uses it, running alongside the front end
    rather than after it.

    ``memref_copy.c`` is vendored from PNNL's soda-benchmarks
    (``scripts/lib/memref_copy.c``), which is Apache-2.0 with LLVM exceptions.
    It differs from MLIR's own ``memrefCopy`` in avoiding the dynamic ``alloca``
    that HLS backends reject.
    '''

    def __init__(self):
        super().__init__()

        self.set_dataroot("siliconcompiler", "python://siliconcompiler")
        self.add_parameter("source", "file",
                           "C source compiled to LLVM IR for linking into the kernel. "
                           "The module it produces is named after it, so a source of "
                           "'helpers.c' yields 'helpers.ll'.",
                           defvalue="tools/mlir/data/memref_copy.c",
                           dataroot="siliconcompiler")

    def set_mlir_source(self, source: Union[str, Path],
                        dataroot: Optional[str] = None,
                        step: Optional[str] = None, index: Optional[str] = None) -> None:
        """Sets the C source compiled into the support module.

        Args:
            source (str or Path): Path to the C source.
            dataroot (str, optional): The dataroot used to resolve relative paths.
            step (str, optional): The step to apply this configuration to.
            index (str, optional): The index to apply this configuration to.
        """
        with self.active_dataroot(self._get_active_dataroot(dataroot)):
            self.set("var", "source", source, step=step, index=index)

    def _get_runtime_ir(self) -> Optional[str]:
        '''Name of the module this task produces, or None if no source is set.

        The source's basename with an ``.ll`` extension, which is what
        :class:`~siliconcompiler.tools.mlir.link.LinkTask` receives in its
        inputs -- it picks the module up as "the upstream module that is not the
        kernel", so the name only has to be stable, not known.
        '''
        source = self.get("var", "source")
        if not source:
            return None
        return os.path.splitext(os.path.basename(source))[0] + ".ll"

    def task(self) -> str:
        return "runtime"

    def parse_version(self, stdout: str) -> str:
        # clang version 19.1.5
        # Ubuntu clang version 16.0.6 (15)
        for line in stdout.splitlines():
            fields = line.split()
            if "version" in fields:
                return fields[fields.index("version") + 1]
        return None

    def setup(self):
        super().setup()

        # clang comes from the same install as llvm-link, so the IR this
        # produces and the IR it is merged into are the same vintage. A machine
        # whose clang is called something else -- clang-16, say -- overrides the
        # binary with set_exe() rather than through a parameter of its own.
        self.set_exe("clang", vswitch="--version")
        # Opaque pointers, which MLIR's own IR uses, became the default in 15.
        self.add_version(">=15.0.0")

        self.set_threads(1)

        # The output is named after the source, so there is nothing to declare
        # until there is one. 'source' is required, so a run that got this far
        # without one stops at validation.
        runtime_ir = self._get_runtime_ir()
        if runtime_ir:
            self.add_output_file(file=runtime_ir)

        self.add_required_key("var", "source")

    def runtime_options(self):
        options = super().runtime_options()

        # -O0 keeps the loop structure the HLS tool has to schedule; optimizing
        # here would only make it harder to read back out.
        options.extend(["-S", "-emit-llvm", "-O0"])
        options.extend(["-o", os.path.join("outputs", self._get_runtime_ir())])
        options.append(self.find_files("var", "source"))

        return options

    def post_process(self):
        super().post_process()

        # MLIR-generated IR carries neither a target triple nor a data layout,
        # and llvm-link refuses to merge two modules that disagree about them.
        output = os.path.join("outputs", self._get_runtime_ir())
        if not os.path.exists(output):
            # A failed node never wrote it, and post_process() runs either way.
            # The real error is the one worth reading, so nothing is added to it.
            return

        with sc_open(output) as f:
            lines = f.readlines()

        with open(output, "w") as f:
            f.writelines(line for line in lines
                         if not line.startswith(("target datalayout", "target triple")))

        # Counted after the rewrite, so the metric describes the module
        # llvm-link is handed rather than what clang emitted.
        self._record_output_lines(output)
