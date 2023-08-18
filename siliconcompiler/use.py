# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.

from siliconcompiler import Chip


class PDK(Chip):
    """
    Object for configuring a process development kit.
    This is the main object used for configuration and data for a PDK
    within the SiliconCompiler platform.

    This inherits all methods from :class:`~siliconcompiler.Chip`.

    Args:
        chip (Chip): A real only copy of the parent chip.
        name (string): Name of the PDK.
    Examples:
        >>> siliconcompiler.PDK(chip, "asap7")
        Creates a flow object with name "asap7".
    """
    def __init__(self, chip, name):
        super().__init__(name)
        self.logger = chip.logger


class FPGA(Chip):
    """
    Object for configuring an FPGA
    This is the main object used for configuration and data for a FPGA
    within the SiliconCompiler platform.

    This inherits all methods from :class:`~siliconcompiler.Chip`.

    Args:
        chip (Chip): A real only copy of the parent chip.
        name (string): Name of the FPGA.
    Examples:
        >>> siliconcompiler.FPGA(chip, "lattice_ice40")
        Creates a flow object with name "lattice_ice40".
    """
    def __init__(self, chip, name):
        super().__init__(name)
        self.logger = chip.logger


class Library(Chip):
    """
    Object for configuring a library.
    This is the main object used for configuration and data for a library
    within the SiliconCompiler platform.

    This inherits all methods from :class:`~siliconcompiler.Chip`.

    Args:
        chip (Chip): A real only copy of the parent chip.
        name (string): Name of the library.
    Examples:
        >>> siliconcompiler.Library(chip, "asap7sc7p5t")
        Creates a library object with name "asap7sc7p5t".
    """
    def __init__(self, chip, name):
        super().__init__(name)
        self.logger = chip.logger


class Flow(Chip):
    """
    Object for configuring a flow.
    This is the main object used for configuration and data for a flow
    within the SiliconCompiler platform.

    This inherits all methods from :class:`~siliconcompiler.Chip`.

    Args:
        chip (Chip): A real only copy of the parent chip.
        name (string): Name of the flow.
    Examples:
        >>> siliconcompiler.Flow(chip, "asicflow")
        Creates a flow object with name "asicflow".
    """
    def __init__(self, chip, name):
        super().__init__(name)
        self.logger = chip.logger


class Checklist(Chip):
    """
    Object for configuring a checklist.
    This is the main object used for configuration and data for a checklist
    within the SiliconCompiler platform.

    This inherits all methods from :class:`~siliconcompiler.Chip`.

    Args:
        chip (Chip): A real only copy of the parent chip.
        name (string): Name of the checklist.
    Examples:
        >>> siliconcompiler.Checklist(chip, "tapeout")
        Creates a checklist object with name "tapeout".
    """
    def __init__(self, chip, name):
        super().__init__(name)
        self.logger = chip.logger
