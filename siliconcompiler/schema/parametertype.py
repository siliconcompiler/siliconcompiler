import re
from collections.abc import Iterable
from pathlib import Path, PureWindowsPath


class NodeType:
    """
    Schema type decoding and encoding class.

    Args:
        sctype (str or :class:`NodeType`): schema type
    """
    __list = re.compile(r"^\[(.*)\]$")
    __tuple = re.compile(r"^\((.*)\)$")
    __set = re.compile(r"^\{(.*)\}$")
    __enum = re.compile(r"^<(.*)>$")
    __basetypes = re.compile(r"^(<(.*)>|int|float|str|bool|file|dir)$")

    def __init__(self, sctype):
        if isinstance(sctype, NodeType):
            self.__type = sctype.type
        elif isinstance(sctype, str):
            self.__type = NodeType.parse(sctype)
        else:
            self.__type = sctype

    def __str__(self):
        return NodeType.encode(self.__type)

    @property
    def type(self):
        return self.__type

    @staticmethod
    def parse(sctype):
        """
        Parses a schema type string.
        """

        if isinstance(sctype, NodeType):
            return sctype.type

        if not isinstance(sctype, str):
            return sctype

        if NodeType.__basetypes.match(sctype):
            if NodeType.__enum.match(sctype):
                return NodeEnumType(*sctype[1:-1].split(","))
            return sctype
        if NodeType.__list.match(sctype):
            return [NodeType.parse(sctype[1:-1])]
        if NodeType.__set.match(sctype):
            return set([NodeType.parse(sctype[1:-1])])
        if NodeType.__tuple.match(sctype):
            tupletypes = []
            typletype = ""
            for ttype in sctype[1:-1].split(","):
                typletype += ttype
                try:
                    tupletypes.append(NodeType.parse(typletype))
                    typletype = ""
                except ValueError:
                    typletype += ","
            return tuple(tupletypes)
        raise ValueError(sctype)

    @staticmethod
    def encode(sctype):
        """
        Encodes a schema type into a string.
        """

        if isinstance(sctype, NodeType):
            sctype = sctype.type

        if isinstance(sctype, list):
            return f"[{NodeType.encode(sctype[0])}]"

        if isinstance(sctype, tuple):
            return f"({','.join([NodeType.encode(sct) for sct in sctype])})"

        if isinstance(sctype, set):
            return f"{{{','.join([NodeType.encode(sct) for sct in sctype])}}}"

        if isinstance(sctype, NodeEnumType):
            return str(sctype)

        if isinstance(sctype, str):
            return sctype

        raise ValueError(f"{sctype} not a recognized type")

    @staticmethod
    def contains(value, check):
        """
        Check if the type contains a specific type.
        """
        if check in (list, tuple, set, NodeEnumType):
            if isinstance(value, check):
                return True
        if isinstance(value, list):
            return NodeType.contains(value[0], check)
        if isinstance(value, tuple):
            return any([NodeType.contains(v, check) for v in value])
        return value == check

    @staticmethod
    def to_tcl(value, sctype):
        '''
        Recursive helper function for converting Python values to safe TCL
        values, based on the SC type string.
        '''

        if isinstance(sctype, list):
            if value is None:
                return '[list ]'
            # Recurse into each item of list
            valstr = ' '.join(NodeType.to_tcl(v, sctype[0]) for v in value)
            return f'[list {valstr}]'

        if isinstance(sctype, set):
            if value is None:
                return '[list ]'
            # Recurse into each item of list
            sctype = list(sctype)[0]
            valstr = ' '.join(NodeType.to_tcl(v, sctype) for v in value)
            return f'[list {valstr}]'

        if isinstance(sctype, tuple):
            if value is None:
                return '[list ]'
            valstr = ' '.join(NodeType.to_tcl(v, subtype) for v, subtype in zip(value, sctype))
            return f'[list {valstr}]'

        if value is None:
            return ''

        if sctype == 'str' or isinstance(sctype, NodeEnumType):
            # Escape string by surrounding it with "" and escaping the few
            # special characters that still get considered inside "". We don't
            # use {}, since this requires adding permanent backslashes to any
            # curly braces inside the string.
            # Source: https://www.tcl.tk/man/tcl8.4/TclCmd/Tcl.html (section [4] on)
            escaped_val = (value.replace('\\', '\\\\')  # escape '\' to avoid backslash substitution
                                                        # (do this first, since other replaces
                                                        # insert '\')
                                .replace('[', '\\[')    # escape '[' to avoid command substitution
                                .replace('$', '\\$')    # escape '$' to avoid variable substitution
                                .replace('"', '\\"'))   # escape '"' to avoid string terminating
            return '"' + escaped_val + '"'
        if sctype == 'bool':
            return 'true' if value else 'false'

        if sctype == 'int':
            return str(value)

        if sctype == 'float':
            return f"{value:.9g}"

        if sctype in ('file', 'dir'):
            # Replace $VAR with $env(VAR) for tcl
            value = re.sub(r'\${?(\w+)}?', r'$env(\1)', value)
            # Same escapes as applied to string, minus $ (since we want to resolve env vars).
            escaped_val = (value.replace('\\', '\\\\')  # escape '\' to avoid backslash substitution
                                                        # (do this first, since other replaces
                                                        # insert '\')
                                .replace('[', '\\[')    # escape '[' to avoid command substitution
                                .replace('"', '\\"'))   # escape '"' to avoid string terminating
            return '"' + escaped_val + '"'

        raise TypeError(f'{sctype} is not a supported type')

    @staticmethod
    def normalize(value, sctype):
        """
        Normalizes a value into the appropriate datatype.
        """

        if isinstance(sctype, NodeType):
            return NodeType.normalize(value, sctype.type)

        if isinstance(sctype, list):
            sctype = sctype[0]

            # Need to try 2 different recursion strategies - if value is a list already, then we can
            # recurse on it directly. However, if that doesn't work, then it might be a
            # list-of-lists/tuples that needs to be wrapped in an outer list, so we try that.
            if isinstance(value, (list, set, tuple)):
                try:
                    return [NodeType.normalize(v, sctype) for v in value]
                except ValueError:
                    pass

            return [NodeType.normalize(v, sctype) for v in [value]]

        if isinstance(sctype, set):
            sctype = list(sctype)[0]

            # Need to try 2 different recursion strategies - if value is a list already, then we can
            # recurse on it directly. However, if that doesn't work, then it might be a
            # list-of-lists/tuples that needs to be wrapped in an outer list, so we try that.
            if isinstance(value, (list, set, tuple)):
                try:
                    return set([NodeType.normalize(v, sctype) for v in value])
                except ValueError:
                    pass

            return set([NodeType.normalize(v, sctype) for v in [value]])

        if isinstance(sctype, tuple):
            if value is None:
                return None

            sctype = [*sctype]

            if isinstance(value, str):
                if NodeType.__tuple.match(value):
                    value = value[1:-1].split(',')
                else:
                    value = value.split(',')
            elif not isinstance(value, (list, tuple)):
                valuetype = type(value)
                if isinstance(value, Iterable):
                    value = ",".join(value)
                raise ValueError(f"({value}) ({valuetype}) cannot be converted to tuple")

            if len(value) != len(sctype):
                raise ValueError(f"({','.join(value)}) does not have {len(sctype)} entries")
            return tuple(
                NodeType.normalize(v, base_type)
                for v, base_type in zip(value, sctype))

        if value is None:
            return None

        if isinstance(value, (list, tuple, set)):
            if len(value) == 1:
                return NodeType.normalize(list(value)[0], sctype)
            raise ValueError(f"\"{type(value)}\" unable to convert to {sctype}")

        if sctype == 'bool':
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                value = value.strip().lower()
                if value == 'true' or value == 't':
                    return True
                if value == 'false' or value == 'f':
                    return False
            if isinstance(value, (int, float)):
                return value != 0
            raise ValueError(f"\"{value}\" unable to convert to boolean")

        try:
            if sctype == 'int':
                return int(value)

            if sctype == 'float':
                return float(value)
        except ValueError:
            raise ValueError(f"\"{value}\" unable to convert to {sctype}")

        if sctype == 'str':
            if isinstance(value, str):
                return value
            elif isinstance(value, bool):
                return str(value).lower()
            else:
                return str(value)

        if sctype in ('file', 'dir'):
            if isinstance(value, (str, Path)):
                # Cast everything to a windows path and convert to posix.
                # https://stackoverflow.com/questions/73682260
                return PureWindowsPath(value).as_posix()
            else:
                raise ValueError(f"{sctype} must be a string or Path, not {type(value)}")

        if isinstance(sctype, NodeEnumType):
            if isinstance(value, str):
                if value in sctype.values:
                    return value
                valid = ", ".join(sorted(sctype.values))
                raise ValueError(f'{value} is not a member of: {valid}')
            else:
                raise ValueError(f"enum must be a string, not a {type(value)}")

        raise ValueError(f'Invalid type specifier: {sctype}')


class NodeEnumType:
    """
    Type for schema data type

    Args:
        values (list of str): list of legal values for this type.
    """

    def __init__(self, *values):
        if not values:
            raise ValueError("enum cannot be empty set")
        self.__values = set(values)

    def __eq__(self, other):
        if isinstance(other, NodeEnumType):
            return self.__values == other.__values
        return False

    def __str__(self):
        return f"<{','.join(sorted(self.__values))}>"

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(tuple(self.__values))

    @property
    def values(self):
        '''
        Returns a set of the legal values for this enum.
        '''
        return self.__values
