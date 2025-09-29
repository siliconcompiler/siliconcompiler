import contextlib
import logging

import os.path

from typing import Tuple

from siliconcompiler.schema.baseschema import BaseSchema
from siliconcompiler.schema.editableschema import EditableSchema
from siliconcompiler.schema.parameter import Parameter, Scope
from siliconcompiler.schema.utils import trim

from siliconcompiler.package import Resolver
from siliconcompiler.utils.paths import collectiondir


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
        cwd = getattr(schema_root, "_Project__cwd", os.getcwd())
        collection_dir = collectiondir(schema_root)

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
        cwd = getattr(schema_root, "_Project__cwd", os.getcwd())
        logger = getattr(schema_root,
                         "logger",
                         logging.getLogger("siliconcompiler.check_filepaths"))
        collection_dir = collectiondir(schema_root)

        return super().check_filepaths(
            ignore_keys=ignore_keys,
            logger=logger,
            collection_dir=collection_dir,
            cwd=cwd)

    def hash_files(self, *keypath, update=True, check=True, verbose=True,
                   missing_ok=False, step=None, index=None):
        '''Generates hash values for a list of parameter files.

        Generates a hash value for each file found in the keypath. If existing
        hash values are stored, this method will compare hashes and trigger an
        error if there's a mismatch. If the update variable is True, the
        computed hash values are recorded in the 'filehash' field of the
        parameter, following the order dictated by the files within the 'value'
        parameter field.

        Files are located using the find_files() function.

        The file hash calculation is performed based on the 'algo' setting.
        Supported algorithms include SHA1, SHA224, SHA256, SHA384, SHA512,
        and MD5.

        Args:
            *keypath(str): Keypath to parameter.
            update (bool): If True, the hash values are recorded in the
                project object manifest.
            check (bool): If True, checks the newly computed hash against
                the stored hash.
            verbose (bool): If True, generates log messages.
            allow_cache (bool): If True, hashing check the cached values
                for specific files, if found, it will use that hash value
                otherwise the hash will be computed.
            skip_missing (bool): If True, hashing will be skipped when missing
                files are detected.

        Returns:
            A list of hash values.

        Examples:
            >>> hashlist = hash_files('input', 'rtl', 'verilog')
            Computes, stores, and returns hashes of files in :keypath:`input, rtl, verilog`.
        '''
        schema_root = self._parent(root=True)
        cwd = getattr(schema_root, "_Project__cwd", os.getcwd())
        logger = getattr(schema_root,
                         "logger",
                         logging.getLogger("siliconcompiler.hash_files"))
        collection_dir = collectiondir(schema_root)

        if verbose:
            logger.info(f"Computing hash value for [{','.join([*self._keypath, *keypath])}]")

        hashes = super().hash_files(*keypath,
                                    missing_ok=missing_ok,
                                    step=step, index=index,
                                    collection_dir=collection_dir,
                                    cwd=cwd)

        if check:
            check_hashes = self.get(*keypath, field="filehash", step=step, index=index)
            if not isinstance(check_hashes, list):
                check_hashes = [check_hashes]

            new_hashes = hashes
            if not isinstance(new_hashes, list):
                new_hashes = [new_hashes]

            for old_hash, new_hash in zip(check_hashes, new_hashes):
                if old_hash is None or new_hash is None:
                    continue
                if old_hash != new_hash:
                    raise ValueError(f"Hash mismatch in [{','.join([*self._keypath, *keypath])}]")

        if update:
            self.set(*keypath, hashes, field="filehash", step=step, index=index)

        return hashes


class PathSchemaSimpleBase(PathSchemaBase):
    def find_files(self, *keypath, missing_ok=False):
        """
        Returns absolute paths to files or directories based on the keypath
        provided.
        The keypath provided must point to a schema parameter of type file, dir,
        or lists of either. Otherwise, it will trigger an error.
        Args:
            keypath (list of str): Variable length schema key list.
            missing_ok (bool): If True, silently return None when files aren't
                found. If False, print an error and set the error flag.
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
        return super().find_files(*keypath,
                                  missing_ok=missing_ok,
                                  step=None, index=None)

    def hash_files(self, *keypath, update=True, check=True, verbose=True, missing_ok=False):
        '''Generates hash values for a list of parameter files.

        Generates a hash value for each file found in the keypath. If existing
        hash values are stored, this method will compare hashes and trigger an
        error if there's a mismatch. If the update variable is True, the
        computed hash values are recorded in the 'filehash' field of the
        parameter, following the order dictated by the files within the 'value'
        parameter field.

        Files are located using the find_files() function.

        The file hash calculation is performed based on the 'algo' setting.
        Supported algorithms include SHA1, SHA224, SHA256, SHA384, SHA512,
        and MD5.

        Args:
            *keypath(str): Keypath to parameter.
            update (bool): If True, the hash values are recorded in the
                project object manifest.
            check (bool): If True, checks the newly computed hash against
                the stored hash.
            verbose (bool): If True, generates log messages.
            allow_cache (bool): If True, hashing check the cached values
                for specific files, if found, it will use that hash value
                otherwise the hash will be computed.
            skip_missing (bool): If True, hashing will be skipped when missing
                files are detected.

        Returns:
            A list of hash values.

        Examples:
            >>> hashlist = hash_files('input', 'rtl', 'verilog')
            Computes, stores, and returns hashes of files in :keypath:`input, rtl, verilog`.
        '''

        return super().hash_files(
            *keypath, update=update, check=check, verbose=verbose,
            missing_ok=missing_ok, step=None, index=None)


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
                    "api: project.set('dataroot', "
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
                    "api: project.set('dataroot', 'freepdk45_data', 'tag', '07ec4aa')"],
                help=trim("""
                    Data directory reference tag. The meaning of the this tag depends on the
                    context of the path.
                    For git, this can be a tag, branch, or commit id. For https this is the version
                    of the file that will be downloaded.
                    """)))

    def __dataroot_section(self) -> "PathSchema":
        root = self._parent(root=True)

        schema = self
        while not schema.valid("dataroot"):
            schema = schema._parent()
            if schema is root:
                break

        return schema

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

        schema = self.__dataroot_section()

        BaseSchema.set(schema, "dataroot", name, "path", path)
        if tag:
            BaseSchema.set(schema, "dataroot", name, "tag", tag)

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

        schema = self.__dataroot_section()

        if not BaseSchema.valid(schema, "dataroot", name):
            raise ValueError(f"{name} is not a recognized source")

        path = BaseSchema.get(schema, "dataroot", name, "path")
        tag = BaseSchema.get(schema, "dataroot", name, "tag")

        resolver = Resolver.find_resolver(path)
        return resolver(name, schema._parent(root=True), path, tag).get_path()

    def _find_files_dataroot_resolvers(self):
        """
        Returns a dictionary of path resolvers data directory handling for find_files

        Returns:
            dictionary of str to resolver mapping
        """
        schema_root = self._parent(root=True)
        schema = self.__dataroot_section()

        if not schema.valid("dataroot"):
            return {}

        resolver_map = {}
        for dataroot in schema.getkeys("dataroot"):
            path = BaseSchema.get(schema, "dataroot", dataroot, "path")
            tag = BaseSchema.get(schema, "dataroot", dataroot, "tag")
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

        schema = self.__dataroot_section()

        if dataroot and not schema.valid("dataroot"):
            raise ValueError(f"{dataroot} is not a recognized dataroot")

        if dataroot and dataroot not in schema.getkeys("dataroot"):
            raise ValueError(f"{dataroot} is not a recognized dataroot")

        with self._active(package=dataroot):
            yield

    def _get_active_dataroot(self, user_dataroot: str) -> str:
        """Resolves and returns the active dataroot to use.

        This method determines the appropriate dataroot based on a specific
        order of precedence:

        1. The dataroot explicitly provided by the user (`user_dataroot`).
        2. The globally active dataroot for the package.
        3. A single, unambiguously defined dataroot.

        Args:
            user_dataroot (str): A dataroot path or name explicitly provided by the
                user. If not None, this value is always returned.

        Returns:
            str | None: The name of the active dataroot. Returns `None` if no
            dataroots are defined and none is required.

        Raises:
            ValueError: If multiple dataroots are defined and the choice is
                ambiguous (i.e., not specified by the user or set as active).
        """
        if user_dataroot is ...:
            return None

        if user_dataroot is not None:
            return user_dataroot

        active_dataroot = self._get_active("package")
        if active_dataroot:
            return active_dataroot

        schema = self.__dataroot_section()

        if not schema.valid("dataroot"):
            return None

        roots = schema.getkeys("dataroot")
        if not roots:
            # No roots defined, so assume no root is needed
            return None

        if len(roots) == 1:
            return roots[0]

        raise ValueError(f"dataroot must be specified, multiple are defined: {', '.join(roots)}")

    def _generate_doc(self, doc,
                      ref_root: str = "",
                      key_offset: Tuple[str] = None,
                      detailed: bool = True):
        from ..schema.docs.utils import build_section, strong, build_table, build_list, \
            code, para
        from docutils import nodes

        section = build_section("Data root", f"{ref_root}-dataroot")

        # This colspec creates two columns of equal width that fill the entire
        # page, and adds line breaks if table cell contents are longer than one
        # line. "\X" is defined by Sphinx, otherwise this is standard LaTeX.
        colspec = r'{|\X{1}{3}|\X{2}{3}|}'

        table = [[strong('Root'), strong('Specifications')]]
        schema = self.__dataroot_section()
        for dataroot in schema.getkeys("dataroot"):
            path = schema.get('dataroot', dataroot, 'path')
            tag = schema.get('dataroot', dataroot, 'tag')

            specs = [nodes.paragraph('', 'Path: ', code(path))]
            if tag:
                specs.append(nodes.paragraph('', 'Tag: ', code(tag)))

            table.append([para(dataroot), build_list(specs)])

        if len(table) == 1:
            return None

        section += build_table(table, colspec=colspec)

        return section
