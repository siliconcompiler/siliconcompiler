import re

import os.path

from typing import List, Optional

from siliconcompiler.utils import sc_open

from siliconcompiler.tools.mlir import MLIRTask


class LinkTask(MLIRTask):
    '''Links support modules into a kernel's LLVM IR with ``llvm-link``.

    Bufferized MLIR lowers ``memref.copy`` to a call to ``memrefCopy``, which an
    HLS backend has no runtime to resolve, so the definition compiled by
    :class:`~siliconcompiler.tools.mlir.compile.RuntimeTask` is merged into the
    module.

    Every upstream module other than the kernel itself is a candidate, whatever
    it is called, so a flow can stage more than one support module without this
    task knowing their names.

    The merge only happens when the kernel actually references
    ``requiredsymbol`` without defining it -- which the unoptimized flow usually
    does not -- so a kernel that has no use for the helpers is not given a dead
    function to carry into synthesis. In that case this is a plain
    ``llvm-link`` pass-through.
    '''

    def __init__(self):
        super().__init__()

        self.add_parameter("runtimesupport", "bool",
                           "link the staged support modules into the kernel",
                           defvalue=True)
        self.add_parameter("requiredsymbol", "str",
                           "only link the support modules when the kernel references "
                           "this symbol without defining it. Empty links them "
                           "unconditionally.",
                           defvalue="memrefCopy")

    def set_mlir_runtimesupport(self, value: bool,
                                step: Optional[str] = None,
                                index: Optional[str] = None) -> None:
        """Enables or disables linking the staged support modules.

        With this off the task is a plain ``llvm-link`` pass-through, and a
        kernel that calls into the helpers reaches the HLS tool with the call
        unresolved.

        Args:
            value (bool): Whether to link the support modules.
            step (str, optional): The step to apply this configuration to.
            index (str, optional): The index to apply this configuration to.
        """
        self.set("var", "runtimesupport", value, step=step, index=index)

    def set_mlir_requiredsymbol(self, symbol: str,
                                step: Optional[str] = None,
                                index: Optional[str] = None) -> None:
        """Sets the symbol whose unresolved reference pulls the support in.

        Args:
            symbol (str): The symbol name, e.g. ``memrefCopy``. An empty string
                links the support modules unconditionally.
            step (str, optional): The step to apply this configuration to.
            index (str, optional): The index to apply this configuration to.
        """
        self.set("var", "requiredsymbol", symbol, step=step, index=index)

    def task(self) -> str:
        return "link"

    def _support_modules(self) -> List[str]:
        '''Names of the upstream modules that are not the kernel.'''
        kernel = f"{self.design_topmodule}.ll"
        return sorted(name for name in self.get_files_from_input_nodes()
                      if name.endswith(".ll") and name != kernel)

    def setup(self):
        super().setup()

        self.set_exe("llvm-link", vswitch="--version")
        self.add_version(">=19.1.0")

        self.set_threads(1)

        self._setup_input("ll", "llvm")
        for module in self._support_modules():
            self.add_input_file(file=module)
        self.add_output_file(ext="ll")

        self.add_required_key("var", "runtimesupport")
        if self.get("var", "requiredsymbol"):
            self.add_required_key("var", "requiredsymbol")

    def __needs_support(self) -> bool:
        '''Reports whether the kernel is missing the symbol the support defines.

        An unset ``requiredsymbol`` means link unconditionally, which is what a
        flow staging a module the kernel is meant to always carry wants.
        '''
        symbol: str = self.get("var", "requiredsymbol")
        if not symbol:
            return True

        referenced = False
        defined = re.compile(rf"^\s*define\b.*@{re.escape(symbol)}\b")
        with sc_open(self._get_input("ll", "llvm")) as f:
            for line in f:
                if defined.match(line):
                    return False
                if f"@{symbol}" in line:
                    referenced = True
        return referenced

    def runtime_options(self):
        options = super().runtime_options()

        options.append("-S")

        modules = self._support_modules()
        if modules and self.get("var", "runtimesupport") and self.__needs_support():
            self.logger.info(f"Linking {', '.join(modules)} into {self.design_topmodule}")
            options.extend(os.path.join("inputs", module) for module in modules)

        options.append(self._get_input("ll", "llvm"))
        options.extend(["-o", os.path.join("outputs", f"{self.design_topmodule}.ll")])

        return options

    def post_process(self):
        super().post_process()

        # The merged module is what the HLS tool reads, so this is the size that
        # matters -- and the difference against the translate node's count is
        # how much the support modules added.
        self._record_output_lines(os.path.join("outputs", f"{self.design_topmodule}.ll"))
