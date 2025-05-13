import copy
import hashlib
import os
import pathlib

import os.path

from .parametertype import NodeType

try:
    from base64 import b64encode, b64decode
    from hashlib import blake2b
    _has_sign = True
except:  # noqa E722
    _has_sign = False


class NodeListValue:
    '''
    Holds the data for a list schema type.

    Args:
        base (:class:`NodeValue`): base type for this list.
    '''

    def __init__(self, base):
        self.__base = base
        self.__values = []

    def getdict(self):
        """
        Returns a schema dictionary.

        Examples:
            >>> value.getdict()
            Returns the complete dictionary for the value
        """

        manifest = {}
        for field in self.fields:
            if field is None:
                continue

            value = self.get(field=field)
            manifest.setdefault(field, []).extend(value)

            if field == "author":
                tmplist = []
                for a in manifest[field]:
                    tmplist.extend(a)
                manifest[field] = tmplist
        return manifest

    def _from_dict(self, manifest, keypath, version):
        '''
        Create a new value based on the provided dictionary.

        Args:
            manifest (dict): Manifest to decide.
            keypath (list of str): Path to the current keypath.
            version (packaging.Version): Version of the dictionary schema
            sctype (str): schema type for this value
        '''

        self.__values.clear()
        for n in range(len(manifest["value"])):
            param = self.__base.copy()
            self.__values.append(param)

            for field in self.fields:
                if field is None:
                    continue

                if len(manifest[field]) <= n:
                    continue
                param.set(manifest[field][n], field=field)

    def get(self, field='value'):
        """
        Returns the value in the specified field

        Args:
            field (str): name of schema field.
        """

        vals = []
        for val in self.__values:
            value = val.get(field=field)
            vals.append(value)
        return vals

    def set(self, value, field='value'):
        """
        Sets the value in a specific field and ensures it has been normalized.

        Returns:
            tuple of modified values

        Args:
            value (any): value to set
            field (str): field to set
        """

        value = NodeType.normalize(value, self.type)

        if field == 'value':
            self.__values.clear()
        else:
            if len(value) != len(self.__values):
                raise ValueError(f"set on {field} field must match number of values")

        modified = list()
        for n in range(len(value)):
            if field == 'value':
                self.__values.append(self.__base.copy())
            self.__values[n].set(value[n], field=field)
            modified.append(self.__values[n])
        return tuple(modified)

    def add(self, value, field='value'):
        """
        Adds the value in a specific field and ensures it has been normalized.

        Returns:
            tuple of modified values

        Args:
            value (any): value to set
            field (str): field to set
        """

        modified = list()
        if field == 'value':
            value = NodeType.normalize(value, self.type)

            for n in range(len(value)):
                self.__values.append(self.__base.copy())
                self.__values[-1].set(value[n], field=field)
                modified.append(self.__values[-1])
        else:
            for val in self.__values:
                val.add(value, field=field)
                modified.append(val)
        return tuple(modified)

    @property
    def fields(self):
        """
        Returns a list of valid fields for this value
        """
        return self.__base.fields

    @property
    def values(self):
        '''
        Returns a copy of the values stored in the list
        '''
        return self.__values.copy()

    def copy(self):
        """
        Returns a copy of this value.
        """

        return copy.deepcopy(self)

    def _set_type(self, sctype):
        sctype = NodeType.parse(sctype)[0]
        self.__base._set_type(sctype)
        for val in self.__values:
            val._set_type(sctype)

    @property
    def type(self):
        """
        Returns the type for this value
        """
        return [self.__base.type]


class NodeValue:
    '''
    Holds the data for a parameter.

    Args:
        sctype (str): type for this value
        value (any): default value for this parameter
    '''

    def __init__(self, sctype, value=None):
        self._set_type(sctype)
        self.__value = value
        self.__signature = None

    @classmethod
    def from_dict(cls, manifest, keypath, version, sctype):
        '''
        Create a new value based on the provided dictionary.

        Args:
            manifest (dict): Manifest to decide.
            keypath (list of str): Path to the current keypath.
            version (packaging.Version): Version of the dictionary schema
            sctype (str): schema type for this value
        '''

        # create a dummy value
        nodeval = cls(sctype)
        nodeval._from_dict(manifest, keypath, version)
        return nodeval

    def getdict(self):
        """
        Returns a schema dictionary.

        Examples:
            >>> value.getdict()
            Returns the complete dictionary for the value
        """

        return {
            "value": self.get(field="value"),
            "signature": self.get(field="signature")
        }

    def _from_dict(self, manifest, keypath, version):
        '''
        Copies the information from the manifest into this value.

        Args:
            manifest (dict): Manifest to decide.
            keypath (list of str): Path to the current keypath.
            version (packaging.Version): Version of the dictionary schema
        '''

        self.set(manifest["value"], field="value")
        self.set(manifest["signature"], field="signature")

    def get(self, field='value'):
        """
        Returns the value in the specified field

        Args:
            field (str): name of schema field.
        """
        if field is None:
            return self
        if field == 'value':
            return copy.deepcopy(self.__value)
        if field == 'signature':
            return self.__signature
        raise ValueError(f"{field} is not a valid field")

    def set(self, value, field='value'):
        """
        Sets the value in a specific field and ensures it has been normalized.

        Returns:
            self

        Args:
            value (any): value to set
            field (str): field to set
        """
        if field == 'value':
            self.__value = NodeType.normalize(value, self.type)
            return self
        if field == 'signature':
            self.__signature = NodeType.normalize(value, "str")
            return self
        raise ValueError(f"{field} is not a valid field")

    def add(self, value, field='value'):
        """
        Not valid for this datatype, will raise a ValueError
        """
        raise ValueError(f"cannot add to {field} field")

    @property
    def fields(self):
        """
        Returns a list of valid fields for this value
        """
        return (None, "value", "signature")

    def copy(self):
        """
        Returns a copy of this value.
        """

        return copy.deepcopy(self)

    def _set_type(self, sctype):
        self.__type = NodeType.parse(sctype)

    def __compute_signature(self, person, key, salt):
        h = blake2b(key=key, salt=salt, person=person)
        for field in self.fields:
            if field is None:
                continue
            if field == 'signature':
                # dont include signature field in hash
                continue
            h.update(str(self.get(field=field)).encode("utf-8"))
        return h.hexdigest()

    def sign(self, person, key, salt=None):
        """
        Generate a signature for this value.

        Args:
            person (str): Identification for this person signing this value
            key (str): Key to used to sign this value
            salt (bytes): salt to use, if not specified, a random number will be selected.
        """
        if not _has_sign:
            raise RuntimeError("encoding not available")

        person = person.encode("utf-8")
        key = key.encode("utf-8")
        if not salt:
            salt = os.urandom(blake2b.SALT_SIZE)
        else:
            salt = salt.encode("utf-8")

        digest = self.__compute_signature(person=person, key=key, salt=salt)
        encode_person = b64encode(person).decode("utf-8")
        encode_salt = b64encode(salt).decode("utf-8")
        self.__signature = f"{encode_person}:{encode_salt}:{digest}"

    def verify_signature(self, person, key):
        """
        Verify the signature of this value.

        Args:
            person (str): Identification for this person signing this value
            key (str): Key to used to sign this value
        """
        if not self.__signature:
            raise ValueError("no signature available")

        if not _has_sign:
            raise RuntimeError("encoding not available")

        key = key.encode("utf-8")
        person = person.encode("utf-8")
        encode_person, encode_salt, digest = self.__signature.split(":")
        check_person = b64encode(person).decode("utf-8")

        if check_person != encode_person:
            raise ValueError(f"{person.decode('utf-8')} does not match signing "
                             f"person: {b64decode(encode_person).decode('utf-8')}")

        decode_salt = b64decode(encode_salt)
        check_digest = self.__compute_signature(person=person, key=key, salt=decode_salt)

        if check_digest == digest:
            return True
        return False

    @property
    def type(self):
        """
        Returns the type for this value
        """
        return self.__type


class PathNodeValue(NodeValue):
    '''
    Holds the path data for a parameter.

    Args:
        type (str): type of path
        value (any): default value for this parameter
    '''

    def __init__(self, type, value=None):
        super().__init__(type, value=value)
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
            self.__filehash = NodeType.normalize(value, "str")
            return self
        if field == 'package':
            self.__package = NodeType.normalize(value, "str")
            return self
        return super().set(value, field=field)

    def __resolve_collection_path(self, path, collection_dir):
        try:
            collected_paths = os.listdir(collection_dir)
            if not collected_paths:
                return None
        except FileNotFoundError:
            return None

        path_paths = pathlib.PurePosixPath(path).parts
        for n in range(len(path_paths)):
            # Search through the path elements to see if any of the previous path parts
            # have been imported

            n += 1
            basename = str(pathlib.PurePosixPath(*path_paths[0:n]))
            endname = str(pathlib.PurePosixPath(*path_paths[n:]))

            import_name = PathNodeValue.generate_hashed_path(basename, self.__package)
            if import_name not in collected_paths:
                continue

            abspath = os.path.join(collection_dir, import_name)
            if endname:
                abspath = os.path.join(abspath, endname)
            abspath = os.path.abspath(abspath)
            if os.path.exists(abspath):
                return abspath

        return None

    @staticmethod
    def resolve_env_vars(path, envvars=None):
        """
        Resolve environment variables in a path.

        Returns the expended path.

        Args:
            path (str): path to expand
            envvars (dict): environmental variables to use during resolution.
        """

        if not path:
            return path

        # Handle environmental expansions
        if not envvars:
            envvars = {}

        # Resolve env vars and user home
        env_save = os.environ.copy()
        os.environ.update(envvars)
        path = os.path.expandvars(path)
        path = os.path.expanduser(path)
        os.environ.clear()
        os.environ.update(env_save)

        return path

    def resolve_path(self, envvars=None, search=None, collection_dir=None):
        """
        Resolve the path of this value.

        Returns the absolute path if found, otherwise raises a FileNotFoundError.

        Args:
            envvars (dict): environmental variables to use during resolution.
            search (list of paths): list of paths to search to check for the path.
            collection_dir (path): path to collection directory.
        """
        value = self.get()
        if value is None:
            return None

        # Handle environmental expansions
        value = PathNodeValue.resolve_env_vars(value, envvars=envvars)

        # Check collections path
        if collection_dir:
            collect_path = self.__resolve_collection_path(value, collection_dir)
            if collect_path:
                return collect_path

        if os.path.isabs(value) and os.path.exists(value):
            return value

        # Search for file
        if search is None:
            search = [os.getcwd()]

        for searchdir in search:
            abspath = os.path.abspath(os.path.join(searchdir, value))
            if os.path.exists(abspath):
                return abspath

        # File not found
        raise FileNotFoundError(value)

    @staticmethod
    def generate_hashed_path(path, package):
        '''
        Utility to map file to an unambiguous name based on its path.

        The mapping looks like:
        path/to/file.ext => file_<hash('path/to')>.ext

        Args:
            path (str): path to directory or file
            package (str): name of package this file belongs to
        '''
        path = pathlib.PurePosixPath(path)
        ext = ''.join(path.suffixes)

        # strip off all file suffixes to get just the bare name
        barepath = path
        while barepath.suffix:
            barepath = pathlib.PurePosixPath(barepath.stem)
        filename = str(barepath.parts[-1])

        if not package:
            package = ''
        else:
            package = f'{package}:'

        path_to_hash = f'{package}{str(path.parent)}'

        pathhash = hashlib.sha1(path_to_hash.encode('utf-8')).hexdigest()

        return f'{filename}_{pathhash}{ext}'

    def get_hashed_filename(self):
        '''
        Utility to map file to an unambiguous name based on its path.

        The mapping looks like:
        path/to/file.ext => file_<hash('path/to')>.ext
        '''
        return PathNodeValue.generate_hashed_path(self.get(), self.__package)

    def hash(self, function, **kwargs):
        """
        Compute the hash for this path.

        Keyword arguments are derived from :meth:`resolve_path`.

        Args:
            function (str): name of hashing function to use.
        """
        raise NotImplementedError

    @staticmethod
    def hash_directory(dirname, hashobj=None, hashfunction=None):
        """
        Compute the hash for this directory.

        Args:
            dirname (path): directory to hash
            hashobj (hashlib.): hashing object
            hashfunction (str): name of hashing function to use
        """

        if dirname is None:
            return None

        if not hashobj:
            hashfunc = getattr(hashlib, hashfunction, None)
            if not hashfunc:
                raise RuntimeError("Unable to hash directory due to missing "
                                   f"hash function: {hashfunction}")
            hashobj = hashfunc()

        all_files = []
        for root, _, files in os.walk(dirname):
            all_files.extend([os.path.join(root, f) for f in files])
        dirhash = None
        hashobj = hashfunc()
        for file in sorted(all_files):
            # Cast everything to a windows path and convert to posix.
            # https://stackoverflow.com/questions/73682260
            posix_path = pathlib.PureWindowsPath(os.path.relpath(file, dirname)).as_posix()
            hashobj.update(posix_path.encode("utf-8"))
            dirhash = PathNodeValue.hash_file(file, hashobj=hashobj)
        return dirhash

    @staticmethod
    def hash_file(filename, hashobj=None, hashfunction=None):
        """
        Compute the hash for this file.

        Args:
            filename (path): file to hash
            hashobj (hashlib.): hashing object
            hashfunction (str): name of hashing function to use
        """

        if filename is None:
            return None

        if not hashobj:
            hashfunc = getattr(hashlib, hashfunction, None)
            if not hashfunc:
                raise RuntimeError("Unable to hash file due to missing "
                                   f"hash function: {hashfunction}")
            hashobj = hashfunc()

        with open(filename, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                hashobj.update(byte_block)
        return hashobj.hexdigest()

    @property
    def fields(self):
        return (*super().fields, "filehash", "package")

    @property
    def type(self):
        raise NotImplementedError


class DirectoryNodeValue(PathNodeValue):
    '''
    Holds the directory data for a parameter.

    Args:
        value (any): default value for this parameter
    '''

    def __init__(self, value=None):
        super().__init__("dir", value=value)

    def hash(self, function, **kwargs):
        """
        Compute the hash for this directory.

        Keyword arguments are derived from :meth:`resolve_path`.

        Args:
            function (str): name of hashing function to use.
        """
        return PathNodeValue.hash_directory(
            self.resolve_path(**kwargs), hashfunction=function)

    @property
    def type(self):
        return "dir"


class FileNodeValue(PathNodeValue):
    '''
    Holds the file data for a parameter.

    Args:
        value (any): default value for this parameter
    '''

    def __init__(self, value=None):
        super().__init__("file", value=value)
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
            self.__date = NodeType.normalize(value, "str")
            return self
        if field == 'author':
            self.__author = NodeType.normalize(value, ["str"])
            return self
        return super().set(value, field=field)

    def add(self, value, field='value'):
        """
        Adds the value in a specific field and ensures it has been normalized.

        Returns:
            self

        Args:
            value (any): value to set
            field (str): field to set
        """

        if field == 'author':
            self.__author.extend(NodeType.normalize(value, ["str"]))
            return self
        return super().add(value, field=field)

    def hash(self, function, **kwargs):
        """
        Compute the hash for this file.

        Keyword arguments are derived from :meth:`resolve_path`.

        Args:
            function (str): name of hashing function to use.
        """
        return PathNodeValue.hash_file(
            self.resolve_path(**kwargs), hashfunction=function)

    @property
    def fields(self):
        return (*super().fields, "date", "author")

    @property
    def type(self):
        return "file"
