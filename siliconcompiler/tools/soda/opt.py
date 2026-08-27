import glob
import os
import shutil

import os.path

from typing import List, Optional, Tuple, Union

from pathlib import Path

from siliconcompiler.tools.soda import SODATask, render_pipeline_options


class OutlineTask(SODATask):
    '''Outlines a kernel from a bufferized MLIR module and lowers it for HLS.

    This is the SODA front end proper. Starting from linalg on buffers, it

    * marks the compute to accelerate and moves it into a ``soda.launch``,
    * outlines that region into a standalone kernel function named
      ``<function>_kernel``,
    * optionally emits a C testbench and Bambu XML test vectors describing the
      kernel's arguments,
    * extracts the kernel into a module of its own, and
    * lowers that module to the LLVM dialect.

    How the lowering is done is what distinguishes the three flows the SODA
    Synthesizer offers, so it is left to the subclasses:
    :class:`BaselineTask`, :class:`OptimizedTask` and :class:`TransformedTask`.

    The outlined kernel is what the HLS tool synthesizes, so the design's
    topmodule has to be its name -- ``forward_kernel`` for the usual model whose
    entry point is ``forward``. The task warns when the two disagree, because
    Bambu would then be pointed at a function that does not exist.
    '''

    def __init__(self):
        super().__init__()

        self.add_parameter("anchorfunc", "str",
                           "name of the function to convert into a SODA kernel. "
                           "Empty converts every function in the module.")
        self.add_parameter("barepointer", "bool",
                           "lower memref arguments to bare pointers instead of memref "
                           "descriptors. Required by the Bambu backend, which has no "
                           "notion of a descriptor struct.",
                           defvalue=True)
        self.add_parameter("noaliasanalysis", "bool",
                           "generate the accelerator code without alias analysis "
                           "annotations (the 'no-aa' option of "
                           "-soda-generate-bambu-accelcode)",
                           defvalue=True)
        self.add_parameter("testbench", "bool",
                           "emit a C testbench covering the kernel's arguments, which "
                           "Bambu can use to simulate the generated RTL",
                           defvalue=True)
        self.add_parameter("xmltestbench", "bool",
                           "emit Bambu XML test vectors and an interface description "
                           "for the kernel's arguments",
                           defvalue=False)
        self.add_parameter("printirafterall", "bool",
                           "print the IR after every pass to the task log. Verbose, but "
                           "the only practical way to see which pass broke a lowering.",
                           defvalue=False)
        self.add_parameter("passplugin", "[file]",
                           "MLIR plugin libraries to load passes from")
        self.add_parameter("dialectplugin", "[file]",
                           "MLIR plugin libraries to load dialects from")

    def set_soda_anchorfunc(self, function: str,
                            step: Optional[str] = None, index: Optional[str] = None) -> None:
        """Sets the function that is converted into a SODA kernel.

        Args:
            function (str): The function name, e.g. ``forward``. An empty string
                converts every function in the module.
            step (str, optional): The step to apply this configuration to.
            index (str, optional): The index to apply this configuration to.
        """
        self.set("var", "anchorfunc", function, step=step, index=index)

    def set_soda_barepointer(self, value: bool,
                             step: Optional[str] = None, index: Optional[str] = None) -> None:
        """Selects the memref calling convention of the lowered kernel.

        Args:
            value (bool): If True, memref arguments become bare pointers. Bambu
                requires this; turning it off produces a kernel that takes MLIR
                memref descriptors and cannot be synthesized.
            step (str, optional): The step to apply this configuration to.
            index (str, optional): The index to apply this configuration to.
        """
        self.set("var", "barepointer", value, step=step, index=index)

    def set_soda_noaliasanalysis(self, value: bool,
                                 step: Optional[str] = None,
                                 index: Optional[str] = None) -> None:
        """Enables or disables the ``no-aa`` accelerator code generation option.

        Args:
            value (bool): If True, the extracted kernel carries no alias
                analysis annotations.
            step (str, optional): The step to apply this configuration to.
            index (str, optional): The index to apply this configuration to.
        """
        self.set("var", "noaliasanalysis", value, step=step, index=index)

    def set_soda_testbench(self, value: bool,
                           step: Optional[str] = None, index: Optional[str] = None) -> None:
        """Enables or disables C testbench generation.

        Args:
            value (bool): Whether to emit ``<kernel>_testbench.c``.
            step (str, optional): The step to apply this configuration to.
            index (str, optional): The index to apply this configuration to.
        """
        self.set("var", "testbench", value, step=step, index=index)

    def set_soda_xmltestbench(self, value: bool,
                              step: Optional[str] = None,
                              index: Optional[str] = None) -> None:
        """Enables or disables XML test vector generation.

        Args:
            value (bool): Whether to emit ``<kernel>_test.xml`` and
                ``<kernel>_interface.xml``.
            step (str, optional): The step to apply this configuration to.
            index (str, optional): The index to apply this configuration to.
        """
        self.set("var", "xmltestbench", value, step=step, index=index)

    def set_soda_printirafterall(self, value: bool,
                                 step: Optional[str] = None,
                                 index: Optional[str] = None) -> None:
        """Enables or disables printing the IR after every pass.

        Args:
            value (bool): Whether to pass ``-mlir-print-ir-after-all``.
            step (str, optional): The step to apply this configuration to.
            index (str, optional): The index to apply this configuration to.
        """
        self.set("var", "printirafterall", value, step=step, index=index)

    def add_soda_passplugin(self, plugin: Union[List[Union[str, Path]], str, Path],
                            dataroot: Optional[str] = None,
                            step: Optional[str] = None, index: Optional[str] = None,
                            clobber: bool = False) -> None:
        """Adds a plugin library to load passes from.

        ``soda-opt`` looks for a separate entry point for passes and for
        dialects, and warns when the one it wants is absent. A library that
        provides both -- the SODA flow's own ``SODAPlugin.so`` does -- therefore
        has to be named to :meth:`add_soda_dialectplugin` as well.

        Args:
            plugin (str, Path or list): Path(s) to the plugin shared object.
            dataroot (str, optional): The dataroot used to resolve relative paths.
            step (str, optional): The step to apply this configuration to.
            index (str, optional): The index to apply this configuration to.
            clobber (bool, optional): If True, replaces the list instead of
                appending to it. Defaults to False.
        """
        with self.active_dataroot(self._get_active_dataroot(dataroot)):
            if clobber:
                self.set("var", "passplugin", plugin, step=step, index=index)
            else:
                self.add("var", "passplugin", plugin, step=step, index=index)

    def add_soda_dialectplugin(self, plugin: Union[List[Union[str, Path]], str, Path],
                               dataroot: Optional[str] = None,
                               step: Optional[str] = None, index: Optional[str] = None,
                               clobber: bool = False) -> None:
        """Adds a plugin library to load dialects from.

        Args:
            plugin (str, Path or list): Path(s) to the plugin shared object.
            dataroot (str, optional): The dataroot used to resolve relative paths.
            step (str, optional): The step to apply this configuration to.
            index (str, optional): The index to apply this configuration to.
            clobber (bool, optional): If True, replaces the list instead of
                appending to it. Defaults to False.
        """
        with self.active_dataroot(self._get_active_dataroot(dataroot)):
            if clobber:
                self.set("var", "dialectplugin", plugin, step=step, index=index)
            else:
                self.add("var", "dialectplugin", plugin, step=step, index=index)

    def _kernel_name(self) -> str:
        '''Name of the outlined kernel, which is the design's topmodule.'''
        return self.design_topmodule

    def _testbench_files(self) -> List[str]:
        '''Names of the argument-description files the enabled passes emit.'''
        files = []
        if self.get("var", "testbench"):
            files.append(f"{self._kernel_name()}_testbench.c")
        if self.get("var", "xmltestbench"):
            files.append(f"{self._kernel_name()}_test.xml")
            files.append(f"{self._kernel_name()}_interface.xml")
        return files

    def setup(self):
        super().setup()

        self.set_exe("soda-opt", vswitch="--version")
        self.add_version(">=19.1.0")

        self.set_threads(1)

        self._setup_input("mlir", "mlir")
        self.add_output_file(ext="mlir")
        for name in self._testbench_files():
            self.add_output_file(file=name)

        for var in ("barepointer", "noaliasanalysis", "testbench", "xmltestbench",
                    "printirafterall"):
            self.add_required_key("var", var)
        if self.get("var", "anchorfunc"):
            self.add_required_key("var", "anchorfunc")
        for var in ("passplugin", "dialectplugin"):
            if self.get("var", var):
                self.add_required_key("var", var)

    def _frontend_options(self) -> List[str]:
        '''The passes that mark, outline and extract the kernel.'''
        options = []

        for plugin in self.find_files("var", "passplugin"):
            options.append(f"--load-pass-plugin={plugin}")
        for plugin in self.find_files("var", "dialectplugin"):
            options.append(f"--load-dialect-plugin={plugin}")

        anchor = self.get("var", "anchorfunc")
        if anchor:
            options.append(f"--convert-all-to-soda=anchor-func={anchor}")
        else:
            options.append("--convert-all-to-soda")

        options.append("-soda-outline-bambu-code")

        bare = "using-bare-ptr" if self.get("var", "barepointer") else ""
        if self.get("var", "testbench"):
            options.append(f"-soda-extract-arguments-to-c-testbench={bare}")
        if self.get("var", "xmltestbench"):
            options.append(f"-soda-extract-arguments-to-xml={bare}")

        if self.get("var", "noaliasanalysis"):
            options.append("-soda-generate-bambu-accelcode=no-aa")
        else:
            options.append("-soda-generate-bambu-accelcode")

        return options

    def _lowering_options(self) -> List[str]:
        '''The passes that lower the extracted kernel to the LLVM dialect.'''
        raise NotImplementedError("must be implemented by the flow-specific task")

    def _bare_pointer_option(self) -> Tuple[str, Optional[bool]]:
        '''The bare-pointer calling convention, as a
        :func:`~siliconcompiler.tools.soda.render_pipeline_options` entry.

        Its value is True or None rather than True or False: every soda-opt
        pipeline takes this as a bare flag and has no way to say "off" other
        than leaving the option out.
        '''
        return ("use-bare-ptr-memref-call-conv",
                True if self.get("var", "barepointer") else None)

    def runtime_options(self):
        options = super().runtime_options()

        options.extend(self._frontend_options())
        options.extend(self._lowering_options())
        options.append("--convert-func-to-llvm")

        if self.get("var", "printirafterall"):
            options.append("-mlir-print-ir-after-all")

        options.append(self._get_input("mlir", "mlir"))
        options.extend(["-o", os.path.join("outputs", f"{self.design_topmodule}.mlir")])

        return options

    def post_process(self):
        super().post_process()

        # The argument-description passes write to the working directory, named
        # after the outlined kernel. Collect them into outputs/ so the flow can
        # hand them to the HLS tool.
        for expected, pattern in ((f"{self._kernel_name()}_testbench.c", "*_testbench.c"),
                                  (f"{self._kernel_name()}_test.xml", "*_test.xml"),
                                  (f"{self._kernel_name()}_interface.xml", "*_interface.xml")):
            if expected not in self._testbench_files():
                continue

            found = sorted(glob.glob(pattern))
            if not found:
                raise FileNotFoundError(
                    f"soda-opt did not emit {expected}; no file matching {pattern} was "
                    "produced. The module may have no kernel to outline.")

            if expected not in found:
                kernel = os.path.basename(found[0]).rsplit("_", 1)[0]
                self.logger.warning(
                    f"soda-opt outlined a kernel named '{kernel}', but the design "
                    f"topmodule is '{self.design_topmodule}'. The HLS tool is pointed at "
                    f"the topmodule, so set the design's topmodule to '{kernel}' (or "
                    "name the entry function with set_soda_anchorfunc) or synthesis "
                    "will fail.")

            shutil.copy2(found[0], os.path.join("outputs", expected))

        # Last, so that a module with no kernel to outline still reports that
        # above rather than failing here on the file soda-opt never wrote.
        self._record_output_lines(os.path.join("outputs", f"{self.design_topmodule}.mlir"))


class BaselineTask(OutlineTask):
    '''Lowers the outlined kernel with no HLS-oriented optimization.

    This is the SODA flow's ``baseline``: the kernel goes straight from linalg
    to the LLVM dialect, so the resulting RTL shows what the HLS tool makes of
    unoptimized code. It is the reference the other two flows are measured
    against.
    '''

    def task(self) -> str:
        return "baseline"

    def _lowering_options(self) -> List[str]:
        pipeline = render_pipeline_options([
            self._bare_pointer_option(),
        ])
        if pipeline:
            return [f"-lower-all-to-llvm={pipeline}"]
        return ["-lower-all-to-llvm"]


class OptimizedTask(OutlineTask):
    '''Lowers the outlined kernel through the SODA optimization pipeline for Bambu.

    This is the SODA flow's ``optimized``: before lowering, the kernel is tiled,
    given local buffers, unrolled and scalar-replaced, which is where most of
    the area and latency difference against the baseline comes from. Every stage
    of that pipeline is exposed here so a design can be swept over it.
    '''

    def __init__(self):
        super().__init__()

        self.add_parameter("tilesize", "int<0..>",
                           "unified tile size applied to every affine loop. 0 disables "
                           "tiling.",
                           defvalue=0)
        self.add_parameter("permutation", "[int]",
                           "loop permutation map. Its length must match the number of "
                           "affine loops in the kernel.")
        self.add_parameter("fullunrolls", "int<0..>",
                           "number of times the full-unroll pass is applied",
                           defvalue=1)
        self.add_parameter("buffertrick", "bool",
                           "generate local buffers for the loop nest and drop their "
                           "deallocations, so the kernel works out of local memory",
                           defvalue=True)
        self.add_parameter("allocapromotion", "bool",
                           "promote heap buffers to the stack",
                           defvalue=True)
        self.add_parameter("maxallocsize", "int<1..>",
                           "largest buffer promoted to the stack, in bytes",
                           defvalue=4096)
        self.add_parameter("maxmemrefrank", "int<1..>",
                           "highest memref rank promoted to the stack",
                           defvalue=3)
        self.add_parameter("scalarreplacement", "bool",
                           "replace redundant affine memory operations with scalars",
                           defvalue=True)

    def set_soda_tilesize(self, size: int,
                          step: Optional[str] = None, index: Optional[str] = None) -> None:
        """Sets the unified affine loop tile size.

        Args:
            size (int): The tile size, applied to every affine loop. 0 disables
                tiling.
            step (str, optional): The step to apply this configuration to.
            index (str, optional): The index to apply this configuration to.
        """
        self.set("var", "tilesize", size, step=step, index=index)

    def add_soda_permutation(self, permutation: Union[int, List[int]],
                             step: Optional[str] = None,
                             index: Optional[str] = None,
                             clobber: bool = False) -> None:
        """Adds to the loop permutation map.

        Args:
            permutation (int or list of int): The permutation, e.g.
                ``[1, 2, 0]``. Its length must match the number of affine loops
                in the kernel, counting the loops tiling introduces.
            step (str, optional): The step to apply this configuration to.
            index (str, optional): The index to apply this configuration to.
            clobber (bool, optional): If True, overwrites the existing map.
                Defaults to False.
        """
        if clobber:
            self.set("var", "permutation", permutation, step=step, index=index)
        else:
            self.add("var", "permutation", permutation, step=step, index=index)

    def set_soda_fullunrolls(self, count: int,
                             step: Optional[str] = None, index: Optional[str] = None) -> None:
        """Sets how many times the full-unroll pass is applied.

        Each application unrolls one more level of the loop nest, so this trades
        area against latency directly.

        Args:
            count (int): The number of full-unroll passes.
            step (str, optional): The step to apply this configuration to.
            index (str, optional): The index to apply this configuration to.
        """
        self.set("var", "fullunrolls", count, step=step, index=index)

    def set_soda_buffertrick(self, value: bool,
                             step: Optional[str] = None, index: Optional[str] = None) -> None:
        """Enables or disables local buffer generation for the loop nest.

        Args:
            value (bool): Whether to generate local buffers.
            step (str, optional): The step to apply this configuration to.
            index (str, optional): The index to apply this configuration to.
        """
        self.set("var", "buffertrick", value, step=step, index=index)

    def set_soda_allocapromotion(self, value: bool,
                                 step: Optional[str] = None,
                                 index: Optional[str] = None) -> None:
        """Enables or disables promoting heap buffers to the stack.

        Args:
            value (bool): Whether to promote buffers.
            step (str, optional): The step to apply this configuration to.
            index (str, optional): The index to apply this configuration to.
        """
        self.set("var", "allocapromotion", value, step=step, index=index)

    def set_soda_maxallocsize(self, size: int,
                              step: Optional[str] = None, index: Optional[str] = None) -> None:
        """Sets the largest buffer, in bytes, that is promoted to the stack.

        Args:
            size (int): The size limit in bytes.
            step (str, optional): The step to apply this configuration to.
            index (str, optional): The index to apply this configuration to.
        """
        self.set("var", "maxallocsize", size, step=step, index=index)

    def set_soda_maxmemrefrank(self, rank: int,
                               step: Optional[str] = None, index: Optional[str] = None) -> None:
        """Sets the highest memref rank promoted to the stack.

        Args:
            rank (int): The rank limit.
            step (str, optional): The step to apply this configuration to.
            index (str, optional): The index to apply this configuration to.
        """
        self.set("var", "maxmemrefrank", rank, step=step, index=index)

    def set_soda_scalarreplacement(self, value: bool,
                                   step: Optional[str] = None,
                                   index: Optional[str] = None) -> None:
        """Enables or disables scalar replacement of redundant memory operations.

        Args:
            value (bool): Whether to run scalar replacement.
            step (str, optional): The step to apply this configuration to.
            index (str, optional): The index to apply this configuration to.
        """
        self.set("var", "scalarreplacement", value, step=step, index=index)

    def task(self) -> str:
        return "optimized"

    def setup(self):
        super().setup()

        for var in ("tilesize", "fullunrolls", "buffertrick", "allocapromotion",
                    "maxallocsize", "maxmemrefrank", "scalarreplacement"):
            self.add_required_key("var", var)
        if self.get("var", "permutation"):
            self.add_required_key("var", "permutation")

    def _lowering_options(self) -> List[str]:
        tilesize = self.get("var", "tilesize")
        permutation = self.get("var", "permutation")

        # The pipeline options are all "remove this optimization" switches, so
        # a knob that is on contributes nothing to the command line.
        promote = self.get("var", "allocapromotion")

        pipeline = render_pipeline_options([
            self._bare_pointer_option(),
            ("affine-tile-size", tilesize if tilesize else None),
            ("permutation-map", ",".join(str(p) for p in permutation) if permutation else None),
            ("number-of-full-unrolls", self.get("var", "fullunrolls")),
            ("no-buffer-trick", None if self.get("var", "buffertrick") else True),
            ("no-alloca-promotion", None if promote else True),
            ("max-alloc-size-in-bytes", self.get("var", "maxallocsize") if promote else None),
            ("max-rank-of-allocated-memref", self.get("var", "maxmemrefrank") if promote else None),
            ("no-scalar-replacement", None if self.get("var", "scalarreplacement") else True),
        ])

        return [f"-soda-opt-pipeline-for-bambu={pipeline}"]


class TransformedTask(OutlineTask):
    '''Lowers the outlined kernel under a transform dialect schedule.

    This is the SODA flow's ``transformed``: instead of the fixed optimization
    pipeline, the kernel is rewritten by a schedule written in MLIR's transform
    dialect, which the interpreter applies before the schedule is erased and the
    kernel is lowered. It is how a design expresses an optimization strategy the
    pipeline's knobs cannot.

    The schedule is an ordinary MLIR file; PNNL's own recipes are named
    ``transform.mlir``.
    '''

    def __init__(self):
        super().__init__()

        self.add_parameter("schedule", "file",
                           "transform dialect schedule applied to the outlined kernel")

    def set_soda_schedule(self, schedule: Union[str, Path],
                          dataroot: Optional[str] = None,
                          step: Optional[str] = None, index: Optional[str] = None) -> None:
        """Sets the transform dialect schedule to apply.

        Args:
            schedule (str or Path): Path to the schedule, an MLIR file holding a
                ``transform.named_sequence @__transform_main``.
            dataroot (str, optional): The dataroot used to resolve relative paths.
            step (str, optional): The step to apply this configuration to.
            index (str, optional): The index to apply this configuration to.
        """
        with self.active_dataroot(self._get_active_dataroot(dataroot)):
            self.set("var", "schedule", schedule, step=step, index=index)

    def task(self) -> str:
        return "transformed"

    def setup(self):
        super().setup()

        self.add_required_key("var", "schedule")

    def _lowering_options(self) -> List[str]:
        schedule = self.find_files("var", "schedule")

        options = [
            f"--transform-preload-library=transform-library-paths={schedule}",
            "--transform-interpreter",
            "--soda-transform-erase-schedule",
        ]

        pipeline = render_pipeline_options([
            self._bare_pointer_option(),
        ])
        if pipeline:
            options.append(f"--lower-all-to-llvm={pipeline}")
        else:
            options.append("--lower-all-to-llvm")

        return options
