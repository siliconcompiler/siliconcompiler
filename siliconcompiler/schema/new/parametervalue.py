import copy
import re
from pathlib import Path


class NodeEnumType:
    def __init__(self, *values):
        if not values:
            raise ValueError("enum cannot be empty set")
        self.__values = set(values)

    def __eq__(self, other):
        if isinstance(other, NodeEnumType):
            return self.__values == other.__values
        return False

    def __str__(self):
        return f"enum<{','.join(sorted(self.__values))}>"

    def __repr__(self):
        return str(self)

    @property
    def values(self):
        return self.__values


class NodeValue:
    '''
    '''

    __list = re.compile(r"^\[(.*)\]$")
    __tuple = re.compile(r"^\((.*)\)$")
    __enum = re.compile(r"^enum<(.*)>$")
    __basetypes = re.compile(r"^(enum<(.*)>|int|float|str|bool|file|dir)$")

    def __init__(self, sctype, value=None):
        self._set_type(sctype)
        self.__value = value
        self.__signature = None

    @staticmethod
    def _parse_type(sctype):
        if NodeValue.__basetypes.match(sctype):
            if NodeValue.__enum.match(sctype):
                return NodeEnumType(*sctype[5:-1].split(","))
            return sctype
        if NodeValue.__list.match(sctype):
            return [NodeValue._parse_type(sctype[1:-1])]
        if NodeValue.__tuple.match(sctype):
            tupletypes = []
            typletype = ""
            for ttype in sctype[1:-1].split(","):
                typletype += ttype
                try:
                    tupletypes.append(NodeValue._parse_type(typletype))
                    typletype = ""
                except ValueError:
                    typletype += ","
            return tuple(tupletypes)
        raise ValueError(sctype)

    @staticmethod
    def normalize(value, sctype):
        if isinstance(sctype, list):
            sctype = sctype[0]

            # Need to try 2 different recursion strategies - if value is a list already, then we can
            # recurse on it directly. However, if that doesn't work, then it might be a
            # list-of-lists/tuples that needs to be wrapped in an outer list, so we try that.
            if isinstance(value, (list, set, tuple)):
                try:
                    return [NodeValue.normalize(v, sctype) for v in value]
                except TypeError:
                    pass

            return [NodeValue.normalize(v, sctype) for v in [value]]

        if isinstance(sctype, tuple):
            sctype = [*sctype]

            # TODO: make parsing more robust to support tuples-of-tuples
            if isinstance(value, str):
                value = value[1:-1].split(',')
            elif not (isinstance(value, tuple) or isinstance(value, list)):
                raise TypeError

            if len(value) != len(sctype):
                raise TypeError
            return tuple(
                NodeValue.normalize(v, base_type)
                for v, base_type in zip(value, sctype))

        if value is None:
            return None

        if isinstance(value, (list, tuple, set)):
            if len(value) == 1:
                return NodeValue.normalize(list(value)[0], sctype)
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
                return str(value)
            else:
                raise TypeError(f"{sctype} must be a string or Path, not {type(value)}")

        if isinstance(sctype, NodeEnumType):
            if isinstance(value, str):
                if value in sctype.values:
                    return value
                valid = ", ".join(sorted(sctype.values))
                raise ValueError(f'{value} is not a member of: {valid}')
            else:
                raise TypeError(f"enum must be a string, not a {type(value)}")

        raise ValueError(f'Invalid type specifier: {sctype}')

    @classmethod
    def from_dict(cls, manifest, keypath, version, sctype):
        # create a dummy value
        nodeval = cls(sctype)
        nodeval._from_dict(manifest, keypath, version)
        return nodeval

    def getdict(self):
        return {
            "value": self.get(field="value"),
            "signature": self.get(field="signature")
        }

    def _from_dict(self, manifest, keypath, version):
        self.set(manifest["value"], field="value")
        self.set(manifest["signature"], field="signature")

    def get(self, field='value'):
        # TODO: normalization of value needed
        if field == 'value':
            return copy.deepcopy(self.__value)
        if field == 'signature':
            return self.__signature
        raise ValueError(f"{field} is not a valid field")

    def set(self, value, field='value'):
        if field == 'value':
            self.__value = NodeValue.normalize(value, self.type)
            return
        if field == 'signature':
            self.__signature = NodeValue.normalize(value, "str")
            return
        raise ValueError(f"{field} is not a valid field")

    @property
    def fields(self):
        return ("value", "signature")

    def copy(self):
        return copy.deepcopy(self)

    def _set_type(self, sctype):
        self.__type = NodeValue._parse_type(sctype)

    @property
    def type(self):
        return self.__type


class DirectoryNodeValue(NodeValue):
    '''
    '''

    def __init__(self, value=None):
        super().__init__("dir", value=value)
        self.__filehash = None
        self.__package = None

    def getdict(self):
        return {
            **super().getdict(),
            "filehash": self.get(field="filehash"),
            "package": self.get(field="package")
        }

    def _from_dict(self, manifest, keypath, version):
        super()._from_dict(manifest, keypath, version)

        self.set(manifest["filehash"], field="filehash")
        self.set(manifest["package"], field="package")

    def get(self, field='value'):
        if field == 'filehash':
            return self.__filehash
        if field == 'package':
            return self.__package
        return super().get(field=field)

    def set(self, value, field='value'):
        if field == 'filehash':
            self.__filehash = NodeValue.normalize(value, "str")
            return
        if field == 'package':
            self.__package = NodeValue.normalize(value, "str")
            return
        super().set(value, field=field)

    @property
    def fields(self):
        return (*super().fields, "filehash", "package")

    @property
    def type(self):
        return "dir"


class FileNodeValue(DirectoryNodeValue):
    '''
    '''

    def __init__(self, value=None):
        super().__init__(value=value)
        self._set_type("file")
        self.__date = None
        self.__author = []

    def getdict(self):
        return {
            **super().getdict(),
            "date": self.get(field="date"),
            "author": self.get(field="author")
        }

    def _from_dict(self, manifest, keypath, version):
        super()._from_dict(manifest, keypath, version)

        self.set(manifest["date"], field="date")
        self.set(manifest["author"], field="author")

    def get(self, field='value'):
        if field == 'date':
            return self.__date
        if field == 'author':
            return self.__author.copy()
        return super().get(field=field)

    def set(self, value, field='value'):
        if field == 'date':
            self.__date = NodeValue.normalize(value, "str")
            return
        if field == 'author':
            self.__author = NodeValue.normalize(value, ["str"])
            return
        super().set(value, field=field)

    @property
    def fields(self):
        return (*super().fields, "date", "author")

    @property
    def type(self):
        return "file"
