import copy
from pathlib import Path


class NodeValue:
    '''
    '''

    def __init__(self, sctype, value=None):
        self.__type = sctype
        self.__value = value
        self.__signature = None

    @staticmethod
    def normalize(value, sctype):
        if sctype.startswith('['):
            base_type = sctype[1:-1]

            # Need to try 2 different recursion strategies - if value is a list already, then we can
            # recurse on it directly. However, if that doesn't work, then it might be a
            # list-of-lists/tuples that needs to be wrapped in an outer list, so we try that.
            if isinstance(value, (list, set, tuple)):
                try:
                    return [NodeValue.normalize(v, base_type) for v in value]
                except TypeError:
                    pass

            return [NodeValue.normalize(v, base_type) for v in [value]]

        if sctype.startswith('('):
            base_type = sctype[1:-1]

            # TODO: make parsing more robust to support tuples-of-tuples
            if isinstance(value, str):
                value = value[1:-1].split(',')
            elif not (isinstance(value, tuple) or isinstance(value, list)):
                raise TypeError

            base_types = base_type.split(',')
            if len(value) != len(base_types):
                raise TypeError
            return tuple(
                NodeValue.normalize(v, base_type)
                for v, base_type in zip(value, base_types))

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

        if value is None:
            return None

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
            elif isinstance(value, (list, tuple, set)):
                raise ValueError(f"\"{type(value)}\" unable to convert to {sctype}")
            else:
                return str(value)

        if sctype in ('file', 'dir'):
            if isinstance(value, (str, Path)):
                return str(value)
            else:
                raise TypeError(f"{sctype} must be a string or Path, not {type(value)}")

        if sctype.startswith('enum'):
            enum = sctype[5:-1]
            if not enum:
                raise RuntimeError("enum cannot be empty set")
            enum = enum.split(",")

            if isinstance(value, str):
                if value in enum:
                    return value
                valid = ", ".join(enum)
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
        self.__type = sctype

    @staticmethod
    def _make_enum(enum):
        return f"enum<{','.join(sorted(set(enum)))}>"

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
            self.__author = NodeValue.normalize(value, "[str]")
            return
        super().set(value, field=field)

    @property
    def fields(self):
        return (*super().fields, "date", "author")

    @property
    def type(self):
        return "file"
