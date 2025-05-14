# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

import argparse
import copy
import re
import shlex

from enum import Enum

from .parametervalue import NodeValue, DirectoryNodeValue, FileNodeValue, NodeListValue
from .parametertype import NodeType, NodeEnumType


class Scope(Enum):
    '''
    Enum for scope Schema parameters
    '''
    GLOBAL = 'global'
    JOB = 'job'
    SCRATCH = 'scratch'


class PerNode(Enum):
    '''
    Enum for pernode Schema parameters
    '''
    NEVER = 'never'
    OPTIONAL = 'optional'
    REQUIRED = 'required'

    def is_never(self):
        '''
        Returns true is this is 'never'
        '''
        return self == PerNode.NEVER


class Parameter:
    '''
    Leaf nodes in the schema. This holds all the information for a given keypath.

    Args:
        type (str): type for the parameter, see
            :class:`.parametertype.NodeType` for supported types.
        require (bool): require field
        defvalue (any): defvalue field
        scope (:class:`.Scope`): scope field
        copy (bool): copy field
        lock (bool): bool field
        hashalgo (str): hashalgo field
        notes (str): notes field
        unit (str): unit field
        shorthelp (str): shorthelp field
        switch (list of str): switch field
        example (list of str): example field
        help (str): help field
        pernode (:class:`.PerNode`): pernode field
    '''

    GLOBAL_KEY = 'global'

    def __init__(self,
                 type,
                 require=False,
                 defvalue=None,
                 scope=Scope.JOB,
                 copy=False,
                 lock=False,
                 hashalgo='sha256',
                 notes=None,
                 unit=None,
                 shorthelp=None,
                 switch=None,
                 example=None,
                 help=None,
                 pernode=PerNode.NEVER):

        self.__type = NodeType.parse(type)
        self.__scope = Scope(scope)
        self.__lock = lock
        self.__require = require

        if switch is None:
            switch = []
        elif isinstance(switch, str):
            switch = [switch]
        self.__switch = switch

        self.__shorthelp = shorthelp

        if example is None:
            example = []
        elif isinstance(example, str):
            example = [example]
        self.__example = example

        self.__help = help

        self.__notes = notes

        if self.__type == 'bool':
            if defvalue is None:
                defvalue = False

        self.__pernode = PerNode(pernode)

        self.__setdefvalue(defvalue)

        self.__node = {}

        self.__unit = None
        if unit is not None and \
                (NodeType.contains(self.__type, 'int') or NodeType.contains(self.__type, 'float')):
            self.__unit = str(unit)

        self.__hashalgo = None
        self.__copy = None
        if NodeType.contains(self.__type, 'dir') or NodeType.contains(self.__type, 'file'):
            self.__hashalgo = str(hashalgo)
            self.__copy = bool(copy)

    def __setdefvalue(self, defvalue):
        if NodeType.contains(self.__type, 'file'):
            base = FileNodeValue(defvalue)
            if isinstance(self.__type, list):
                self.__defvalue = NodeListValue(base)
            else:
                self.__defvalue = base
        elif NodeType.contains(self.__type, 'dir'):
            base = DirectoryNodeValue(defvalue)
            if isinstance(self.__type, list):
                self.__defvalue = NodeListValue(base)
            else:
                self.__defvalue = base
        else:
            if isinstance(self.__type, list):
                self.__defvalue = NodeListValue(NodeValue(self.__type[0]))
                if defvalue:
                    self.__defvalue.set(defvalue)
            else:
                self.__defvalue = NodeValue(self.__type, value=defvalue)

    def __str__(self):
        return str(self.getvalues())

    def get(self, field='value', step=None, index=None):
        """
        Returns the value in a parameter field.

        Args:
            field (str): Parameter field to fetch.
            step (str): Step name to access for parameters that may be specified
                on a per-node basis.
            index (str): Index name to access for parameters that may be specified
                on a per-node basis.

        Returns:
            Field value for the parameter.

        Examples:
            >>> value = param.get()
            Returns the value stored in the parameter.
        """

        self.__assert_step_index(field, step, index)

        if field in self.__defvalue.fields:
            if isinstance(index, int):
                index = str(index)

            try:
                return self.__node[step][index].get(field=field)
            except KeyError:
                if self.__pernode == PerNode.REQUIRED:
                    return self.__defvalue.get(field=field)

            try:
                return self.__node[step][Parameter.GLOBAL_KEY].get(field=field)
            except KeyError:
                pass

            try:
                return self.__node[Parameter.GLOBAL_KEY][Parameter.GLOBAL_KEY].get(field=field)
            except KeyError:
                return self.__defvalue.get(field=field)
        elif field == "type":
            return NodeType.encode(self.__type)
        elif field == "scope":
            return self.__scope
        elif field == "lock":
            return self.__lock
        elif field == "switch":
            return copy.deepcopy(self.__switch)
        elif field == "shorthelp":
            return self.__shorthelp
        elif field == "example":
            return copy.deepcopy(self.__example)
        elif field == "help":
            return self.__help
        elif field == "notes":
            return self.__notes
        elif field == "pernode":
            return self.__pernode
        elif field == "unit":
            return self.__unit
        elif field == "hashalgo":
            return self.__hashalgo
        elif field == "copy":
            return self.__copy
        elif field == "require":
            return self.__require

        raise ValueError(f'"{field}" is not a valid field')

    def __assert_step_index(self, field, step, index):
        if field not in self.__defvalue.fields:
            if step is not None or index is not None:
                raise KeyError(
                    'step and index are only valid for'
                    f': {", ".join([field for field in self.__defvalue.fields if field])}')
            return

        if self.__pernode == PerNode.NEVER and (step is not None or index is not None):
            raise KeyError('use of step and index are not valid')

        if self.__pernode == PerNode.REQUIRED and (step is None or index is None):
            raise KeyError('step and index are required')

        if step is None and index is not None:
            raise KeyError('step is required if index is provided')

        # Step and index for default should be accessed set_/get_default
        if step == 'default':
            raise KeyError('illegal step name: default is reserved')

        if index == 'default':
            raise KeyError('illegal index name: default is reserved')

    def set(self, value, field='value', step=None, index=None, clobber=True):
        '''
        Sets a parameter field.

        Args:
            value (any): Value to set.
            field (str): Parameter field to set.
            clobber (bool): Existing value is overwritten if True.
            step (str): Step name to set for parameters that may be specified
                on a per-node basis.
            index (str): Index name to set for parameters that may be specified
                on a per-node basis.

        Examples:
            >>> param.set('top')
            Sets the value to 'top'
        '''

        if field != "lock":
            if self.__lock:
                return False

        if self.is_set(step, index) and not clobber:
            return False

        self.__assert_step_index(field, step, index)

        if field in self.__defvalue.fields:
            if isinstance(index, int):
                index = str(index)

            step = step if step is not None else Parameter.GLOBAL_KEY
            index = index if index is not None else Parameter.GLOBAL_KEY

            if step not in self.__node:
                self.__node[step] = {}
            if index not in self.__node[step]:
                self.__node[step][index] = self.__defvalue.copy()

            return self.__node[step][index].set(value, field=field)
        elif field == "type":
            self.__type = NodeType.normalize(value, "str")
        elif field == "scope":
            if isinstance(value, Scope):
                self.__scope = value
            else:
                self.__scope = Scope(NodeType.normalize(value,
                                                        NodeEnumType(*[v.value for v in Scope])))
        elif field == "lock":
            self.__lock = NodeType.normalize(value, "bool")
        elif field == "switch":
            self.__switch = NodeType.normalize(value, ["str"])
        elif field == "shorthelp":
            self.__shorthelp = NodeType.normalize(value, "str")
        elif field == "example":
            self.__example = NodeType.normalize(value, ["str"])
        elif field == "help":
            self.__help = NodeType.normalize(value, "str")
        elif field == "notes":
            self.__notes = NodeType.normalize(value, "str")
        elif field == "pernode":
            if isinstance(value, PerNode):
                self.__pernode = value
            else:
                self.__pernode = PerNode(NodeType.normalize(value,
                                                            NodeEnumType(
                                                                *[v.value for v in PerNode])))
        elif field == "unit":
            self.__unit = NodeType.normalize(value, "str")
        elif field == "hashalgo":
            self.__hashalgo = NodeType.normalize(value, "str")
        elif field == "copy":
            self.__copy = NodeType.normalize(value, "bool")
        elif field == "require":
            self.__require = NodeType.normalize(value, "bool")
        else:
            raise ValueError(f'"{field}" is not a valid field')

        return True

    def add(self, value, field='value', step=None, index=None):
        '''
        Adds item(s) to a list.

        Args:
            value (any): Value to add.
            field (str): Parameter field to modify.
            step (str): Step name to modify for parameters that may be specified
                on a per-node basis.
            index (str): Index name to modify for parameters that may be specified
                on a per-node basis.

        Examples:
            >>> param.add('hello.v')
            Adds the file 'hello.v' the parameter.
        '''

        if self.__lock:
            return False

        self.__assert_step_index(field, step, index)

        if field in self.__defvalue.fields:
            if not self.is_list() and field == 'value':
                raise ValueError("add can only be used on lists")

            if isinstance(index, int):
                index = str(index)

            step = step if step is not None else Parameter.GLOBAL_KEY
            index = index if index is not None else Parameter.GLOBAL_KEY

            if step not in self.__node:
                self.__node[step] = {}
            if index not in self.__node[step]:
                self.__node[step][index] = self.__defvalue.copy()

            return self.__node[step][index].add(value, field=field)
        elif field == "switch":
            self.__switch.extend(NodeType.normalize(value, ["str"]))
        elif field == "example":
            self.__example.extend(NodeType.normalize(value, ["str"]))
        else:
            raise ValueError(f'"{field}" is not a valid field')

        return True

    def unset(self, step=None, index=None):
        '''
        Unsets a schema parameter.

        This method effectively undoes any previous calls to :meth:`set()` made to
        the given keypath and step/index. For parameters with required or no
        per-node values, unsetting a parameter always causes it to revert to its
        default value, and future calls to :meth:`set()` with ``clobber=False`` will
        once again be able to modify the value.

        If you unset a particular step/index for a parameter with optional
        per-node values, note that the newly returned value will be the global
        value if it has been set. To completely return the parameter to its
        default state, the global value has to be unset as well.

        ``unset()`` has no effect if called on a parameter that has not been
        previously set.

        Args:
            step (str): Step name to unset for parameters that may be specified
                on a per-node basis.
            index (str): Index name to unset for parameters that may be specified
                on a per-node basis.
        '''

        if self.__lock:
            return False

        if isinstance(index, int):
            index = str(index)

        step = step if step is not None else Parameter.GLOBAL_KEY
        index = index if index is not None else Parameter.GLOBAL_KEY

        try:
            del self.__node[step][index]
        except KeyError:
            # If this key doesn't exist, silently continue - it was never set
            pass

        return True

    def getdict(self, include_default=True):
        """
        Returns a schema dictionary.

        Args:
            include_default (boolean): If true will include default values

        Returns:
            A schema dictionary

        Examples:
            >>> param.getdict()
            Returns the complete dictionary for the parameter
        """

        dictvals = {
            "type": NodeType.encode(self.__type),
            "require": self.__require,
            "scope": self.__scope.value,
            "lock": self.__lock,
            "switch": self.__switch.copy(),
            "shorthelp": self.__shorthelp,
            "example": self.__example.copy(),
            "help": self.__help,
            "notes": self.__notes,
            "pernode": self.__pernode.value,
            "node": {}
        }

        for step in self.__node:
            dictvals["node"][step] = {}
            for index, val in self.__node[step].items():
                dictvals["node"][step][index] = val.getdict()

        if include_default:
            dictvals["node"].setdefault("default", {})["default"] = self.__defvalue.getdict()

        if self.__unit:
            dictvals["unit"] = self.__unit
        if self.__hashalgo:
            dictvals["hashalgo"] = self.__hashalgo
        if self.__copy is not None:
            dictvals["copy"] = self.__copy
        return dictvals

    @classmethod
    def from_dict(cls, manifest, keypath, version):
        '''
        Create a new parameter based on the provided dictionary.

        Args:
            manifest (dict): Manifest to decide.
            keypath (list of str): Path to the current keypath.
            version (packaging.Version): Version of the dictionary schema
        '''

        # create a dummy param
        param = cls("str")
        param._from_dict(manifest, keypath, version)
        return param

    def _from_dict(self, manifest, keypath, version):
        '''
        Copies the information from the manifest into this parameter.

        Args:
            manifest (dict): Manifest to decide.
            keypath (list of str): Path to the current keypath.
            version (packaging.Version): Version of the dictionary schema
        '''

        if self.__lock:
            return

        if version and version > (0, 50, 0):
            self.__type = NodeType.parse(manifest["type"])
        else:
            if "enum" in manifest:
                self.__type = NodeType.parse(
                    re.sub("enum", f"<{','.join(manifest['enum'])}>", manifest['type']))
            else:
                self.__type = NodeType.parse(manifest["type"])

        self.__require = manifest.get("require", self.__require)
        self.__scope = Scope(manifest.get("scope", self.__scope))
        self.__lock = manifest.get("lock", self.__lock)
        self.__switch = manifest.get("switch", self.__switch)
        self.__shorthelp = manifest.get("shorthelp", self.__shorthelp)
        self.__example = manifest.get("example", self.__example)
        self.__help = manifest.get("help", self.__help)
        self.__notes = manifest.get("notes", self.__notes)
        self.__pernode = PerNode(manifest.get("pernode", self.__pernode))
        self.__node = {}

        self.__unit = manifest.get("unit", self.__unit)
        self.__hashalgo = manifest.get("hashalgo", self.__hashalgo)
        self.__copy = manifest.get("copy", self.__copy)

        requires_set = NodeType.contains(self.__type, tuple) or NodeType.contains(self.__type, set)

        try:
            defvalue = manifest["node"]["default"]["default"]["value"]
            del manifest["node"]["default"]
        except KeyError:
            defvalue = None

        if requires_set:
            self.__setdefvalue(NodeType.normalize(defvalue, self.__type))
        else:
            self.__setdefvalue(defvalue)

        for step, indexdata in manifest["node"].items():
            self.__node[step] = {}
            for index, nodedata in indexdata.items():
                value = self.__defvalue.copy()
                value._from_dict(nodedata, keypath, version)
                self.__node[step][index] = value

        if requires_set:
            for step, indexdata in self.__node.items():
                for param in indexdata.values():
                    value = param.get()
                    param.set(value)

    def gettcl(self, step=None, index=None):
        """
        Returns a tcl string for this parameter.

        Args:
            step (str): Step name to unset for parameters that may be specified
                on a per-node basis.
            index (str): Index name to unset for parameters that may be specified
                on a per-node basis.
        """

        if self.__pernode == PerNode.REQUIRED and (step is None or index is None):
            return None
        if not self.__pernode.is_never():
            value = self.get(step=step, index=index)
        else:
            value = self.get()

        return NodeType.to_tcl(value, self.__type)

    def getvalues(self, return_defvalue=True):
        """
        Returns all values (global and pernode) associated with a particular parameter.

        Returns a list of tuples of the form (value, step, index). The list is
        in no particular order. For the global value, step and index are None.
        If return_defvalue is True, the default parameter value is added to the
        list in place of a global value if a global value is not set.
        """

        vals = []
        has_global = False
        for step in self.__node:
            for index in self.__node[step]:
                step_arg = None if step == Parameter.GLOBAL_KEY else step
                index_arg = None if index == Parameter.GLOBAL_KEY else index
                if step_arg is None and index_arg is None:
                    has_global = True
                vals.append((self.__node[step][index].get(), step_arg, index_arg))

        if (self.__pernode != PerNode.REQUIRED) and not has_global and return_defvalue:
            vals.append((self.__defvalue.get(), None, None))

        return vals

    def copy(self, key=None):
        """
        Returns a copy of this parameter.

        Args:
            key (list of str): keypath to this schema
        """

        return copy.deepcopy(self)

    # Utility functions
    def is_list(self):
        """
        Returns true is this parameter is a list type
        """

        return isinstance(self.__type, list)

    def is_empty(self):
        '''
        Utility function to check key for an empty value.
        '''

        empty = (None, [])

        values = self.getvalues()
        return all([value in empty for value, _, _ in values])

    def is_set(self, step=None, index=None):
        '''
        Returns whether a user has set a value for this parameter.

        A value counts as set if a user has set a global value OR a value for
        the provided step/index.
        '''
        if Parameter.GLOBAL_KEY in self.__node and \
                Parameter.GLOBAL_KEY in self.__node[Parameter.GLOBAL_KEY] and \
                self.__node[Parameter.GLOBAL_KEY][Parameter.GLOBAL_KEY]:
            # global value is set
            return True

        if step is None:
            return False
        if index is None:
            index = Parameter.GLOBAL_KEY

        return step in self.__node and \
            index in self.__node[step] and \
            self.__node[step][index]

    @property
    def default(self):
        """
        Gets a copy of the default value.
        """
        return self.__defvalue.copy()

    def add_commandline_arguments(self, argparser, *keypath, switchlist=None):
        '''
        Adds commandline arguments for this parameter.

        Args:
            argparser (argparse.ArgumentParser): argument parser to add switches to
            keypath (list of str): keypath where this parameter is located.
            switchlist (list of str): if provided will limited the switched added to
                those in this list

        Returns:
            dest (str): key for argument parsing to lookup values in.
            switches (list of str): list of switches added.
        '''
        if not self.__switch:
            # no switches available to this parameter
            return None, None

        if not switchlist:
            switchlist = []
        elif not isinstance(switchlist, (list, set, tuple)):
            switchlist = [switchlist]

        switches = []
        metavar = None
        for switch in self.__switch:
            switchmatch = re.match(r'(-[\w_]+)\s+(\'([\w]+\s)*<.*>\'|<.*>)', switch)
            gccmatch = re.match(r'(-[\w_]+)(<.*>)', switch)
            plusmatch = re.match(r'(\+[\w_\+]+)(<.*>)', switch)

            if switchmatch:
                switchstr = switchmatch.group(1)
                metavar = switchmatch.group(2)
            elif gccmatch:
                switchstr = gccmatch.group(1)
                metavar = gccmatch.group(2)
            elif plusmatch:
                switchstr = plusmatch.group(1)
                metavar = plusmatch.group(2)
            else:
                raise ValueError(f"unable to process switch information: {switch}")

            if switchlist and switchstr not in switchlist:
                continue

            switches.append(switchstr)

        if not switches:
            return None, None

        # argparse 'dest' must be a string, so join keypath with commas
        dest = '_'.join(keypath)

        if self.__type == "bool":
            # Boolean type arguments
            if self.__pernode.is_never():
                argparser.add_argument(
                    *switches,
                    nargs='?',
                    metavar=metavar,
                    dest=dest,
                    const='true',
                    help=self.__shorthelp,
                    default=argparse.SUPPRESS)
            else:
                argparser.add_argument(
                    *switches,
                    metavar=metavar,
                    nargs='?',
                    dest=dest,
                    action='append',
                    const='true',
                    help=self.__shorthelp,
                    default=argparse.SUPPRESS)
        elif isinstance(self.__type, list) or self.__pernode != PerNode.NEVER:
            # list type arguments
            argparser.add_argument(
                *switches,
                metavar=metavar,
                dest=dest,
                action='append',
                help=self.__shorthelp,
                default=argparse.SUPPRESS)
        else:
            # all the rest
            argparser.add_argument(
                *switches,
                metavar=metavar,
                dest=dest,
                help=self.__shorthelp,
                default=argparse.SUPPRESS)

        return dest, switches

    def parse_commandline_arguments(self, value, *keypath):
        """
        Parse and set the values provided form the commandline parser.

        Args:
            value (str): string from commandline
            keypath (list of str): leypath to this parameter
        """
        num_free_keys = keypath.count('default')

        if num_free_keys > 0:
            valueitem = shlex.split(value)
            if len(valueitem) != num_free_keys + 1:
                raise ValueError(f'Invalid value "{value}" for switch {"/".join(self.__switch)}')

            free_keys = valueitem[0:num_free_keys]
            remainder = valueitem[-1]
            keypath = tuple([free_keys.pop(0) if key == 'default' else key for key in keypath])
        else:
            remainder = value

        step, index = None, None
        if self.__pernode == PerNode.REQUIRED:
            try:
                step, index, val = shlex.split(remainder)
            except ValueError:
                raise ValueError(f'Invalid value "{value}" for switch {"/".join(self.__switch)}: '
                                 'Requires step and index before final value')
        elif self.__pernode == PerNode.OPTIONAL:
            # Split on spaces, preserving items that are grouped in quotes
            items = shlex.split(remainder)
            if len(items) > 3:
                raise ValueError(f'Invalid value "{value}" for switch {"/".join(self.__switch)}: '
                                 'Too many arguments')
            if self.__type == 'bool':
                if len(items) == 3:
                    step, index, val = items
                elif len(items) == 2:
                    step, val = items
                    if val != 'true' and val != 'false':
                        index = val
                        val = 'true'
                elif len(items) == 1:
                    val, = items
                    if val != 'true' and val != 'false':
                        step = val
                        val = 'true'
                else:
                    val = 'true'
            else:
                if len(items) == 3:
                    step, index, val = items
                elif len(items) == 2:
                    step, val = items
                else:
                    val, = items
        else:
            val = remainder

        return keypath, step, index, val
