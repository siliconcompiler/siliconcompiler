import contextlib
import logging

import os.path

from siliconcompiler.schema.baseschema import BaseSchema
from siliconcompiler.schema.editableschema import EditableSchema
from siliconcompiler.schema.parameter import Parameter, Scope
from siliconcompiler.schema.utils import trim

from siliconcompiler.package import Resolver


class PathSchemaBase(BaseSchema):
    '''
    Schema extension to add simpler find_files and check_filepaths
    '''

    def find_files(self, *keypath,
                   missing_ok=False,
                   step=None, index=None):
        """
        Returns absolute paths to files or directories based on the keypath
        provided.

        The keypath provided must point to a schema parameter of type file, dir,
        or lists of either. Otherwise, it will trigger an error.

        Args:
            keypath (list of str): Variable length schema key list.
            missing_ok (bool): If True, silently return None when files aren't
                found. If False, print an error and set the error flag.
            step (str): Step name to access for parameters that may be specified
                on a per-node basis.
            index (str): Index name to access for parameters that may be specified
                on a per-node basis.

        Returns:
            If keys points to a scalar entry, returns an absolute path to that
            file/directory, or None if not found. It keys points to a list
            entry, returns a list of either the absolute paths or None for each
            entry, depending on whether it is found.

        Examples:
            >>> schema.find_files('input', 'verilog')
            Returns a list of absolute paths to source files, as specified in
            the schema.
        """
        schema_root = self._parent(root=True)
        cwd = getattr(schema_root, "cwd", os.getcwd())
        collection_dir = getattr(schema_root, "collection_dir", None)
        if collection_dir:
            collection_dir = collection_dir()

        return super().find_files(*keypath,
                                  missing_ok=missing_ok,
                                  step=step, index=index,
                                  collection_dir=collection_dir,
                                  cwd=cwd)

    def check_filepaths(self, ignore_keys=None):
        '''
        Verifies that paths to all files in manifest are valid.

        Args:
            ignore_keys (list of keypaths): list of keypaths to ignore while checking

        Returns:
            True if all file paths are valid, otherwise False.
        '''
        schema_root = self._parent(root=True)
        cwd = getattr(schema_root, "cwd", os.getcwd())
        logger = getattr(schema_root,
                         "logger",
                         logging.getLogger("siliconcompiler.check_filepaths"))
        collection_dir = getattr(schema_root, "collection_dir", None)
        if collection_dir:
            collection_dir = collection_dir()

        return super().check_filepaths(
            ignore_keys=ignore_keys,
            logger=logger,
            collection_dir=collection_dir,
            cwd=cwd)


class PathSchema(PathSchemaBase):
    '''
    Schema extension to add support for path handling with dataroots
    '''

    def __init__(self):
        super().__init__()

        schema = EditableSchema(self)

        schema.insert(
            'dataroot', 'default', 'path',
            Parameter(
                'str',
                scope=Scope.GLOBAL,
                shorthelp="Data directory path",
                example=[
                    "api: chip.set('dataroot', "
                    "'freepdk45_data', 'path', 'ssh://git@github.com/siliconcompiler/freepdk45/')"],
                help=trim("""
                    Data directory path, this points the location where the data can be
                    retrieved or accessed.
                    Allowed roots:

                    * /path/on/network/drive
                    * file:///path/on/network/drive
                    * git+https://github.com/xyz/xyz
                    * git://github.com/xyz/xyz
                    * git+ssh://github.com/xyz/xyz
                    * ssh://github.com/xyz/xyz
                    * https://github.com/xyz/xyz/archive
                    * https://zeroasic.com/xyz.tar.gz
                    * github://siliconcompiler/lambdapdk/v1.0/asap7.tar.gz
                    * python://siliconcompiler
                    """)))

        schema.insert(
            'dataroot', 'default', 'tag',
            Parameter(
                'str',
                scope=Scope.GLOBAL,
                shorthelp="Data directory reference tag/version",
                example=[
                    "api: chip.set('dataroot', 'freepdk45_data', 'tag', '07ec4aa')"],
                help=trim("""
                    Data directory reference tag. The meaning of the this tag depends on the
                    context of the path.
                    For git, this can be a tag, branch, or commit id. For https this is the version
                    of the file that will be downloaded.
                    """)))

    def set_dataroot(self, name: str, path: str, tag: str = None):
        """
        Registers a data directory by its name with the root and associated tag. If the path
        provided is a file, the path recorded will be the directory the file is located in.

        Args:
            name (str): Data directory name
            path (str): Path to the root of the data directory, can be directory, git url,
                archive url, or path to a file
            tag (str): Reference of the sources, can be commitid, branch name, tag

        Examples:
            >>> schema.set_dataroot('siliconcompiler_data',
                    'git+https://github.com/siliconcompiler/siliconcompiler',
                    'v1.0.0')
            Records the data directory for siliconcompiler_data as a git clone for tag v1.0.0
            >>> schema.set_dataroot('file_data', __file__)
            Records the data directory for file_data as the directory that __file__ is found in.
        """

        if os.path.isfile(path):
            path = os.path.dirname(os.path.abspath(path))

        BaseSchema.set(self, "dataroot", name, "path", path)
        if tag:
            BaseSchema.set(self, "dataroot", name, "tag", tag)

    def get_dataroot(self, name: str) -> str:
        """
        Returns absolute path to the data directory.

        Raises:
            ValueError: is data directory is not found

        Args:
            name (str): name of the data directory to find.

        Returns:
            Path to the directory root.

        Examples:
            >>> schema.get_dataroot('siliconcompiler')
            Returns the path to the root of the siliconcompiler data directory.
        """

        if not BaseSchema.valid(self, "dataroot", name):
            raise ValueError(f"{name} is not a recognized source")

        path = BaseSchema.get(self, "dataroot", name, "path")
        tag = BaseSchema.get(self, "dataroot", name, "tag")

        resolver = Resolver.find_resolver(path)
        return resolver(name, self._parent(root=True), path, tag).get_path()

    def _find_files_dataroot_resolvers(self):
        """
        Returns a dictionary of path resolevrs data directory handling for find_files

        Returns:
            dictionary of str to resolver mapping
        """
        schema_root = self._parent(root=True)
        resolver_map = {}
        for dataroot in self.getkeys("dataroot"):
            path = BaseSchema.get(self, "dataroot", dataroot, "path")
            tag = BaseSchema.get(self, "dataroot", dataroot, "tag")
            resolver = Resolver.find_resolver(path)
            resolver_map[dataroot] = resolver(dataroot, schema_root, path, tag).get_path
        return resolver_map

    @contextlib.contextmanager
    def active_dataroot(self, dataroot: str = None):
        '''
        Use this context to set the dataroot parameter on files and directory parameters.

        Args:
            dataroot (str): name of the dataroot

        Example:
            >>> with schema.active_dataroot("lambdalib"):
            ...     schema.set("file", "top.v")
            Sets the file to top.v and associates lambdalib as the dataroot.
        '''

        if dataroot and dataroot not in self.getkeys("dataroot"):
            raise ValueError(f"{dataroot} is not a recognized dataroot")

        with self._active(package=dataroot):
            yield
