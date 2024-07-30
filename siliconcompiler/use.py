# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.

from siliconcompiler import Chip


class PackageChip(Chip):
    def __init__(self, chip, name, package=None):
        self.__package = package
        super().__init__(name)
        self.logger = chip.logger

    def add(self, *args, field='value', step=None, index=None, package=None):
        if not package:
            package = self.__package
        super().add(*args, field=field, step=step,
                    index=index, package=package)

    def set(self, *args, field='value', clobber=True, step=None, index=None, package=None):
        if not package:
            package = self.__package
        super().set(*args, field=field, clobber=clobber, step=step,
                    index=index, package=package)


class PDK(PackageChip):
    """
    Object for configuring a process development kit.
    This is the main object used for configuration and data for a PDK
    within the SiliconCompiler platform.

    This inherits all methods from :class:`~siliconcompiler.Chip`.

    Args:
        chip (Chip): A real only copy of the parent chip.
        name (string): Name of the PDK.
        package (string): Name of the data source
    Examples:
        >>> siliconcompiler.PDK(chip, "asap7")
        Creates a flow object with name "asap7".
    """


class FPGA(PackageChip):
    """
    Object for configuring an FPGA
    This is the main object used for configuration and data for a FPGA
    within the SiliconCompiler platform.

    This inherits all methods from :class:`~siliconcompiler.Chip`.

    Args:
        chip (Chip): A real only copy of the parent chip.
        name (string): Name of the FPGA.
        package (string): Name of the data source
    Examples:
        >>> siliconcompiler.FPGA(chip, "lattice_ice40")
        Creates a flow object with name "lattice_ice40".
    """


class Library(PackageChip):
    """
    Object for configuring a library.
    This is the main object used for configuration and data for a library
    within the SiliconCompiler platform.

    This inherits all methods from :class:`~siliconcompiler.Chip`.

    Args:
        chip (Chip): A real only copy of the parent chip.
        name (string): Name of the library.
        package (string): Name of the data source
        auto_enable (boolean): If True, will automatically be added to ['option','library'].
            This is only valid for non-logiclibs and macrolibs
    Examples:
        >>> siliconcompiler.Library(chip, "asap7sc7p5t")
        Creates a library object with name "asap7sc7p5t".
    """
    def __init__(self, chip, name, package=None, auto_enable=False):
        super().__init__(chip, name, package=package)

        self.__auto_enable = auto_enable

    def is_auto_enable(self):
        return self.__auto_enable


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
