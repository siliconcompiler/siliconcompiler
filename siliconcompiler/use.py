# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.

from siliconcompiler import Chip


class PackageChip(Chip):
    def __init__(self, *args, package=None):
        # Start with None as init setting will not depend on package
        self.__package = None

        name = args[-1]
        super().__init__(name)

        if len(args) == 2:
            self.logger.warning(f'passing Chip object to {type(self)} is deprecated')

        path = None
        ref = None
        if isinstance(package, (tuple, list)):
            if len(package) == 3:
                package, path, ref = package
            elif len(package) == 2:
                package, path = package
            else:
                raise ValueError(f"{package} should be a 2 or 3 item tuple or list.")
        elif isinstance(package, dict):
            if len(package) == 1:
                info = list(package.values())[0]
                if "path" not in info:
                    raise ValueError(f"{package} should contain a path key.")
                path = info["path"]
                if "ref" in info:
                    ref = info["ref"]

                package = list(package.keys())[0]
            else:
                raise ValueError(f"{package} cannot contain multiple packages.")
        elif isinstance(package, str):
            pass
        else:
            if package is not None:
                raise ValueError(f"{package} is not supported.")

        if path:
            self.register_source(package, path, ref=ref)

        self.__package = package

        # Clear all copy flags since these are libraries, pdks, fpga, etc.
        for key in self.allkeys():
            sc_type = self.get(*key, field='type')
            if 'file' in sc_type or 'dir' in sc_type:
                self.set(*key, False, field='copy')

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

    def input(self, filename, fileset=None, filetype=None, iomap=None,
              step=None, index=None, package=None):
        self._add_input_output('input', filename, fileset, filetype, iomap,
                               step=step, index=index, package=package,
                               quiet=True)

    def output(self, filename, fileset=None, filetype=None, iomap=None,
               step=None, index=None, package=None):
        self._add_input_output('output', filename, fileset, filetype, iomap,
                               step=step, index=index, package=package,
                               quiet=True)


class PDK(PackageChip):
    """
    Object for configuring a process development kit.
    This is the main object used for configuration and data for a PDK
    within the SiliconCompiler platform.

    This inherits all methods from :class:`~siliconcompiler.Chip`.

    Args:
        name (string): Name of the PDK.
        package (string): Name of the data source
    Examples:
        >>> siliconcompiler.PDK("asap7")
        Creates a flow object with name "asap7".
    """


class FPGA(PackageChip):
    """
    Object for configuring an FPGA
    This is the main object used for configuration and data for a FPGA
    within the SiliconCompiler platform.

    This inherits all methods from :class:`~siliconcompiler.Chip`.

    Args:
        name (string): Name of the FPGA.
        package (string): Name of the data source
    Examples:
        >>> siliconcompiler.FPGA("lattice_ice40")
        Creates a flow object with name "lattice_ice40".
    """


class Library(PackageChip):
    """
    Object for configuring a library.
    This is the main object used for configuration and data for a library
    within the SiliconCompiler platform.

    This inherits all methods from :class:`~siliconcompiler.Chip`.

    Args:
        name (string): Name of the library.
        package (string): Name of the data source
        auto_enable (boolean): If True, will automatically be added to ['option','library'].
            This is only valid for non-logiclibs and macrolibs
    Examples:
        >>> siliconcompiler.Library("asap7sc7p5t")
        Creates a library object with name "asap7sc7p5t".
    """
    def __init__(self, *args, package=None, auto_enable=False):
        super().__init__(*args, package=package)

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
        name (string): Name of the flow.
    Examples:
        >>> siliconcompiler.Flow("asicflow")
        Creates a flow object with name "asicflow".
    """
    def __init__(self, *args):
        super().__init__(args[-1])
        if len(args) == 2:
            self.logger.warning(f'passing Chip object to {type(self)} is deprecated')


class Checklist(Chip):
    """
    Object for configuring a checklist.
    This is the main object used for configuration and data for a checklist
    within the SiliconCompiler platform.

    This inherits all methods from :class:`~siliconcompiler.Chip`.

    Args:
        name (string): Name of the checklist.
    Examples:
        >>> siliconcompiler.Checklist("tapeout")
        Creates a checklist object with name "tapeout".
    """
    def __init__(self, *args):
        super().__init__(args[-1])
        if len(args) == 2:
            self.logger.warning(f'passing Chip object to {type(self)} is deprecated')
