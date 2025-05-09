# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

from .baseschema import BaseSchema
from .parametertype import NodeType


class PackageSchema(BaseSchema):
    '''
    This object provides easier access to the package field in the path datatypes.

    Args:
        package (str): name of the package
    '''

    def __init__(self, package=None):
        super().__init__()

        if package is not None and not isinstance(package, str):
            raise ValueError("package must be a string")

        self.__package = package

    def set(self, *args, field='value', clobber=True, step=None, index=None, package=None):
        '''
        Sets a schema parameter field.

        Sets a schema parameter field based on the keypath and value provided in
        the ``*args``. New schema entries are automatically created for keypaths
        that overlap with 'default' entries.

        Args:
            args (list): Parameter keypath followed by a value to set.
            field (str): Parameter field to set.
            clobber (bool): Existing value is overwritten if True.
            step (str): Step name to set for parameters that may be specified
                on a per-node basis.
            index (str): Index name to set for parameters that may be specified
                on a per-node basis.
            package (str): Name of package to associate with this value.

        Examples:
            >>> schema.set('design', 'top')
            Sets the [design] value to 'top'
        '''

        params = super().set(*args, field=field, clobber=clobber, step=step, index=index)

        if field == 'value' and (package or self.__package):
            self.__set_package(params, package or self.__package)

        return params

    def add(self, *args, field='value', step=None, index=None, package=None):
        '''
        Adds item(s) to a schema parameter list.

        Adds item(s) to schema parameter list based on the keypath and value
        provided in the ``*args``.  New schema entries are automatically created
        for keypaths that overlap with 'default' entries.

        Args:
            args (list): Parameter keypath followed by a value to add.
            field (str): Parameter field to modify.
            step (str): Step name to modify for parameters that may be specified
                on a per-node basis.
            index (str): Index name to modify for parameters that may be specified
                on a per-node basis.
            package (str): Name of package to associate with this value.

        Examples:
            >>> schema.add('input', 'rtl', 'verilog', 'hello.v')
            Adds the file 'hello.v' to the [input,rtl,verilog] key.
        '''

        params = super().add(*args, field=field, step=step, index=index)

        if field == 'value' and (package or self.__package):
            self.__set_package(params, package or self.__package)

        return params

    def __set_package(self, params, packages):
        if not isinstance(params, (list, tuple, set)):
            params = [params]

        if not isinstance(packages, (list, tuple, set)):
            packages = [packages]

        if len(params) != len(packages):
            if len(packages) == 1:
                packages = len(params) * packages
            else:
                raise ValueError("unable to determine package mapping")

        for param, package in zip(params, packages):
            if NodeType.contains(param.type, 'file') or NodeType.contains(param.type, 'dir'):
                param.set(package, field='package')
