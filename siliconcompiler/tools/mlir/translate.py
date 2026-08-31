import os
import re

import os.path

from typing import List, Optional, Union

from siliconcompiler.utils import sc_open

from siliconcompiler.tools.mlir import MLIRTask


class TranslateTask(MLIRTask):
    '''Translates an MLIR module into LLVM IR with ``mlir-translate``.

    This is the hand-off from the MLIR world to the LLVM IR that the HLS tool
    reads: the input has already been lowered to the LLVM dialect (by
    :ref:`soda-opt <tool-soda>` or by
    :class:`~siliconcompiler.tools.mlir.opt.LinalgToLLVMTask`), and this task
    emits the textual ``.ll`` for it.

    The translated module is then filtered: MLIR brackets the buffers it
    allocates on the stack with ``llvm.stacksave`` / ``llvm.stackrestore``
    intrinsics, which an HLS backend has no notion of. Those lines are dropped,
    which is what the SODA flow does with ``sed`` at the same point.
    '''

    def __init__(self):
        super().__init__()

        self.add_parameter("action", "str",
                           "mlir-translate action to perform",
                           defvalue="--mlir-to-llvmir")
        self.add_parameter("stripintrinsics", "[str]",
                           "LLVM intrinsics to strip from the translated IR. Any line "
                           "mentioning one of these is removed, which drops both the "
                           "declaration and the calls.",
                           defvalue=["llvm.stacksave.p0", "llvm.stackrestore.p0"])

    def set_mlir_action(self, action: str,
                        step: Optional[str] = None, index: Optional[str] = None) -> None:
        """Sets the ``mlir-translate`` action.

        Args:
            action (str): The action flag, e.g. ``--mlir-to-llvmir``.
            step (str, optional): The step to apply this configuration to.
            index (str, optional): The index to apply this configuration to.
        """
        self.set("var", "action", action, step=step, index=index)

    def add_mlir_stripintrinsics(self, intrinsics: Union[str, List[str]],
                                 step: Optional[str] = None,
                                 index: Optional[str] = None,
                                 clobber: bool = False) -> None:
        """Adds an intrinsic to the list stripped from the translated IR.

        Args:
            intrinsics (str or list of str): Intrinsic name(s) to strip.
            step (str, optional): The step to apply this configuration to.
            index (str, optional): The index to apply this configuration to.
            clobber (bool, optional): If True, overwrites the existing list.
                Clobbering with an empty list keeps the translated module
                exactly as ``mlir-translate`` emitted it. Defaults to False.
        """
        if clobber:
            self.set("var", "stripintrinsics", intrinsics, step=step, index=index)
        else:
            self.add("var", "stripintrinsics", intrinsics, step=step, index=index)

    def task(self) -> str:
        return "translate"

    def setup(self):
        super().setup()

        self.set_exe("mlir-translate", vswitch="--version")
        self.add_version(">=19.1.0")

        self.set_threads(1)

        self._setup_input("mlir", "mlir")
        self.add_output_file(ext="ll")

        self.add_required_key("var", "action")
        if self.get("var", "stripintrinsics"):
            self.add_required_key("var", "stripintrinsics")

    def runtime_options(self):
        options = super().runtime_options()

        options.append(self.get("var", "action"))
        options.append(self._get_input("mlir", "mlir"))
        options.extend(["-o", os.path.join("outputs", f"{self.design_topmodule}.ll")])

        return options

    def post_process(self):
        super().post_process()

        output = os.path.join("outputs", f"{self.design_topmodule}.ll")
        if not os.path.exists(output):
            # A failed node never wrote it, and post_process() runs either way.
            # The real error is the one worth reading, so nothing is added to it.
            return

        intrinsics = self.get("var", "stripintrinsics")
        if not intrinsics:
            # Nothing to strip, but the IR is still handed on, so it is still
            # counted.
            self._record_output_lines(output)
            return

        pattern = re.compile("|".join(re.escape(name) for name in intrinsics))

        with sc_open(output) as f:
            lines = f.readlines()

        kept = [line for line in lines if not pattern.search(line)]
        dropped = len(lines) - len(kept)
        if dropped:
            self.logger.info(f"Stripped {dropped} line(s) referencing "
                             f"{', '.join(intrinsics)} from {self.design_topmodule}.ll")
            with open(output, "w") as f:
                f.writelines(kept)

        # Counted after the rewrite, so the metric describes the IR the
        # downstream node reads rather than what mlir-translate emitted.
        self._record_output_lines(output)
