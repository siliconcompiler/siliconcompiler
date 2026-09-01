import os.path

from typing import List, Optional, Union

from pathlib import Path

from siliconcompiler.tools.mlir import MLIRTask


class OptTask(MLIRTask):
    '''Runs a set of passes over an MLIR file with ``mlir-opt``.

    ``mlir-opt`` takes the passes to run in one of two forms -- a textual
    pipeline (``-pass-pipeline=...``) or an ordered list of individual pass
    flags -- and rejects a command line carrying both. Which form a lowering can
    use is a property of the passes themselves, not a preference: a pipeline can
    nest passes under an operation (``func.func(...)``), while a flag list can
    mix module-level and function-level passes freely.

    So the two forms are two subclasses, :class:`PipelineTask` and
    :class:`PassesTask`, and a lowering inherits from whichever one its passes
    need. Nothing can then be configured into the combination ``mlir-opt``
    refuses.

    This class is the part they share; it is not a task on its own.
    '''

    def __init__(self):
        super().__init__()

        self.add_parameter("passplugin", "[file]",
                           "MLIR plugin libraries to load passes from")
        self.add_parameter("dialectplugin", "[file]",
                           "MLIR plugin libraries to load dialects from")

    def add_mlir_passplugin(self, plugin: Union[List[Union[str, Path]], str, Path],
                            dataroot: Optional[str] = None,
                            step: Optional[str] = None, index: Optional[str] = None,
                            clobber: bool = False) -> None:
        """Adds a plugin library to load passes from.

        The passes it provides can then be named like any other, in either
        :meth:`set_mlir_pipeline` or :meth:`add_mlir_passes`. A library that
        provides a dialect as well has to be named to
        :meth:`add_mlir_dialectplugin` too -- ``mlir-opt`` looks for a separate
        entry point for each, and only warns when the one it wants is absent.

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

    def add_mlir_dialectplugin(self, plugin: Union[List[Union[str, Path]], str, Path],
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

    def setup(self):
        super().setup()

        self.set_exe("mlir-opt", vswitch="--version")
        self.add_version(">=19.1.0")

        self.set_threads(1)

        self._setup_input("mlir", "mlir")
        self.add_output_file(ext="mlir")

        for var in ("passplugin", "dialectplugin"):
            if self.get("var", var):
                self.add_required_key("var", var)

    def _pass_options(self) -> List[str]:
        '''The command line options naming the passes to run.'''
        raise NotImplementedError("must be implemented by the pass-form specific task")

    def _plugin_options(self) -> List[str]:
        '''The options loading the plugin libraries.

        These come first on the command line: a pass a plugin provides is only a
        known pass name once the plugin holding it has been loaded.
        '''
        options = []
        for plugin in self.find_files("var", "passplugin"):
            options.append(f"--load-pass-plugin={plugin}")
        for plugin in self.find_files("var", "dialectplugin"):
            options.append(f"--load-dialect-plugin={plugin}")
        return options

    def runtime_options(self):
        options = super().runtime_options()

        options.extend(self._plugin_options())
        options.extend(self._pass_options())
        options.append(self._get_input("mlir", "mlir"))
        options.extend(["-o", os.path.join("outputs", f"{self.design_topmodule}.mlir")])

        return options

    def post_process(self):
        super().post_process()

        # Both pass forms write the same file, so the count belongs here rather
        # than in each of them.
        self._record_output_lines(os.path.join("outputs", f"{self.design_topmodule}.mlir"))


class PipelineTask(OptTask):
    '''Runs a textual pass pipeline, as ``-pass-pipeline=...``.

    This is the form to use when the passes have to be nested under the
    operation they run on, which the flag list cannot express.

    A subclass says what it runs by overriding :meth:`_pipeline`, which becomes
    the parameter's default; a user can still replace it with
    :meth:`set_mlir_pipeline`.
    '''

    ###############################################################
    # Definition, overridden by each lowering
    ###############################################################
    @property
    def _pipeline(self) -> Optional[str]:
        """
        Textual pass pipeline this task runs when it is not configured otherwise.
        """
        return None

    def __init__(self):
        super().__init__()

        self.add_parameter("pipeline", "str",
                           "textual MLIR pass pipeline, passed as -pass-pipeline",
                           defvalue=self._pipeline)

    def set_mlir_pipeline(self, pipeline: str,
                          step: Optional[str] = None, index: Optional[str] = None) -> None:
        """Sets the textual pass pipeline handed to ``-pass-pipeline``.

        Args:
            pipeline (str): The pass pipeline, e.g.
                ``builtin.module(func.func(canonicalize))``.
            step (str, optional): The step to apply this configuration to.
            index (str, optional): The index to apply this configuration to.
        """
        self.set("var", "pipeline", pipeline, step=step, index=index)

    def task(self) -> str:
        return "pipeline"

    def setup(self):
        super().setup()

        self.add_required_key("var", "pipeline")

    def _pass_options(self) -> List[str]:
        return [f"-pass-pipeline={self.get('var', 'pipeline')}"]


class PassesTask(OptTask):
    '''Runs an ordered list of individual pass flags.

    This is the form to use when the passes are a flat sequence, which is most
    of them, and the only form that can mix module-level and function-level
    passes.

    A subclass says what it runs by overriding :meth:`_passes`, which becomes
    the parameter's default; a user can still change it with
    :meth:`add_mlir_passes`.
    '''

    ###############################################################
    # Definition, overridden by each lowering
    ###############################################################
    @property
    def _passes(self) -> List[str]:
        """
        Ordered pass flags this task runs when it is not configured otherwise.
        """
        return []

    def __init__(self):
        super().__init__()

        self.add_parameter("passes", "[str]",
                           "ordered list of mlir-opt pass flags, e.g. -canonicalize",
                           defvalue=list(self._passes))

    def add_mlir_passes(self, passes: Union[str, List[str]],
                        step: Optional[str] = None, index: Optional[str] = None,
                        clobber: bool = False) -> None:
        """Appends one or more pass flags to the end of the pass list.

        Args:
            passes (str or list of str): The pass flag(s) to append, in the
                order they should run, e.g. ``["-canonicalize", "-cse"]``.
            step (str, optional): The step to apply this configuration to.
            index (str, optional): The index to apply this configuration to.
            clobber (bool, optional): If True, overwrites the existing list --
                which is how a task's own passes are replaced rather than added
                to. Defaults to False.
        """
        if clobber:
            self.set("var", "passes", passes, step=step, index=index)
        else:
            self.add("var", "passes", passes, step=step, index=index)

    def task(self) -> str:
        return "passes"

    def setup(self):
        super().setup()

        self.add_required_key("var", "passes")

    def _pass_options(self) -> List[str]:
        return list(self.get("var", "passes"))


class TosaToLinalgTask(PipelineTask):
    '''Lowers a TOSA module to linalg on tensors.

    This is the first half of the SODA front end's ``tosa_to_linalg`` step: the
    named TOSA operations become their linalg equivalents, still operating on
    tensor values. :class:`BufferizeTask` runs afterwards to put them on
    buffers.

    A pipeline rather than a flag list because every pass here runs on a
    ``func.func``.
    '''

    @property
    def _pipeline(self) -> str:
        """Pass pipeline this task runs."""
        return ("builtin.module(func.func(tosa-to-arith, tosa-to-tensor, "
                "tosa-to-linalg-named, tosa-to-linalg))")

    def task(self) -> str:
        return "tosa2linalg"


class BufferizeTask(PassesTask):
    '''Bufferizes linalg on tensors into linalg on memrefs.

    This is the second half of the SODA front end's ``tosa_to_linalg`` step. The
    result is the ``02_linalg.mlir`` of the SODA flow: linalg operations on
    buffers, with the function results turned into out-parameters, which is the
    form :ref:`soda-opt <tool-soda>` outlines a kernel from.
    '''

    @property
    def _passes(self) -> List[str]:
        """Pass flags this task runs, in order."""
        return [
            "--tosa-to-arith=include-apply-rescale=true",
            "--canonicalize",
            "-convert-tensor-to-linalg",
            "-empty-tensor-to-alloc-tensor",
            "-eliminate-empty-tensors",
            "-one-shot-bufferize=function-boundary-type-conversion=identity-layout-map "
            "bufferize-function-boundaries allow-return-allocs-from-loops "
            "unknown-type-conversion=identity-layout-map",
            "-func-bufferize",
            "-buffer-deallocation-simplification",
            "-bufferization-lower-deallocations",
            "--buffer-results-to-out-params",
            "--canonicalize",
            "-cse",
        ]

    def task(self) -> str:
        return "bufferize"


class LinalgToLLVMTask(PassesTask):
    '''Lowers linalg all the way to the LLVM dialect.

    This is the reference software lowering of the SODA flow (its
    ``linalg_to_llvm`` step), which produces a module that can be translated and
    executed on a CPU. It is not part of the hardware path -- there,
    :ref:`soda-opt <tool-soda>` does the lowering, so that a kernel is outlined
    and optimized for high-level synthesis on the way down.
    '''

    @property
    def _passes(self) -> List[str]:
        """Pass flags this task runs, in order."""
        return [
            "-convert-linalg-to-affine-loops",
            "-expand-strided-metadata",
            "-lower-affine",
            "-convert-scf-to-cf",
            "-convert-complex-to-standard",
            "-convert-vector-to-llvm",
            "--convert-math-to-llvm",
            "--convert-math-to-libm",
            "-arith-expand",
            "-memref-expand",
            "-convert-to-llvm=filter-dialects=memref",
            "-finalize-memref-to-llvm",
            "-convert-arith-to-llvm",
            "-finalize-memref-to-llvm",
            "-convert-complex-to-llvm",
            "-convert-func-to-llvm=use-bare-ptr-memref-call-conv=1",
            "--test-lower-to-llvm",
            "-convert-cf-to-llvm",
            "-reconcile-unrealized-casts",
            "-symbol-dce",
        ]

    def task(self) -> str:
        return "linalg2llvm"
