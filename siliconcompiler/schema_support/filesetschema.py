import contextlib

from pathlib import Path

from typing import List, Tuple, Optional, Union, Iterable, Set

from siliconcompiler import utils

from siliconcompiler.schema_support.pathschema import PathSchema
from siliconcompiler.schema import EditableSchema, Parameter, Scope, BaseSchema
from siliconcompiler.schema.utils import trim


###########################################################################
class FileSetSchema(PathSchema):
    '''
    Schema for storing and managing file sets.

    This class provides methods to add, retrieve, and manage named groups of
    files, known as filesets.
    '''

    def __init__(self):
        '''Initializes the FileSetSchema.'''
        super().__init__()

        schema = EditableSchema(self)

        fileset = 'default'
        filetype = 'default'
        schema.insert(
            'fileset', fileset, 'file', filetype,
            Parameter(
                '[file]',
                scope=Scope.GLOBAL,
                shorthelp="Fileset files",
                example=[
                    "api: schema.set('fileset', 'rtl', 'file', 'verilog', 'mytop.v')",
                    "api: schema.set('fileset', 'testbench', 'file', 'verilog', 'tb.v')"],
                help=trim("""
                List of files grouped as a named set ('fileset'). The exact names of
                filetypes and filesets must match the names used in tasks
                called during flowgraph execution. The files are processed in
                the order specified by the ordered file list.""")))

    ###############################################
    def add_file(self,
                 filename: Union[List[Union[Path, str]], Set[Union[Path, str]],
                                 Tuple[Union[Path, str], ...], Path, str],
                 fileset: Optional[str] = None,
                 filetype: Optional[str] = None,
                 clobber: bool = False,
                 dataroot: Optional[str] = None) -> List[str]:
        """
        Adds files to a fileset.

        Based on the file's extension, this method can often infer the correct
        fileset and filetype. For example:

        * .v -> (source, verilog)
        * .vhd -> (source, vhdl)
        * .sdc -> (constraint, sdc)
        * .lef -> (input, lef)
        * .def -> (input, def)
        * etc.

        Args:
            filename (Path, str, or collection): File path (Path or str), or a collection
                (list, tuple, set) of file paths to add.
            fileset (str): Logical group to associate the file with.
            filetype (str, optional): Type of the file (e.g., 'verilog', 'sdc').
            clobber (bool, optional): If True, clears the list before adding the
                item. Defaults to False.
            dataroot (str, optional): Data directory reference name.

        Raises:
            ValueError: If `fileset` or `filetype` cannot be inferred from
                the file extension.

        Returns:
           list[str]: A list of the file paths that were added.

        Notes:
           * This method normalizes `filename` to a string for consistency.
           * If `filetype` is not specified, it is inferred from the
               file extension.
        """

        if fileset is None:
            fileset = self._get_active("fileset")

        if not isinstance(fileset, str):
            raise ValueError("fileset key must be a string")

        # handle list inputs
        if isinstance(filename, (list, set, tuple)):
            if isinstance(filename, set):
                filename = sorted(filename)
            params = []
            for item in filename:
                params.extend(
                    self.add_file(
                        item,
                        fileset=fileset,
                        clobber=clobber,
                        filetype=filetype,
                        dataroot=dataroot))
            return params

        if filename is None:
            raise ValueError("add_file cannot process None")

        # Normalize value to string in case we receive a pathlib.Path
        filename = str(filename)

        # map extension to default filetype/fileset
        if not filetype:
            ext = utils.get_file_ext(filename)
            filetype = utils.get_default_iomap().get(ext, ext)

        # adding files to dictionary
        with self.active_dataroot(self._get_active_dataroot(dataroot)):
            if clobber:
                return self.set('fileset', fileset, 'file', filetype, filename)
            else:
                return self.add('fileset', fileset, 'file', filetype, filename)

    ###############################################
    def get_file(self,
                 fileset: Optional[str] = None,
                 filetype: Optional[str] = None) -> List[str]:
        """Returns a list of files from one or more filesets.

        Args:
            fileset (str or list[str]): Fileset(s) to query. If not provided,
                the active fileset is used.
            filetype (str or list[str], optional): File type(s) to filter by
                (e.g., 'verilog'). If not provided, all filetypes in the
                fileset are returned.

        Returns:
            list[str]: A list of resolved file paths.
        """

        if fileset is None:
            fileset = self._get_active("fileset")

        if not isinstance(fileset, list):
            fileset = [fileset]

        if filetype and not isinstance(filetype, list):
            filetype = [filetype]

        filelist = []
        for fs in fileset:
            if not isinstance(fs, str):
                raise ValueError("fileset key must be a string")
            # handle scalar+list in argument
            if not filetype:
                filetype = self.getkeys('fileset', fs, 'file')
            # grab the files
            for ftype in filetype:
                filelist.extend(self.find_files('fileset', fs, 'file', ftype))

        return filelist

    ###############################################
    def has_file(self, fileset: Optional[str] = None, filetype: Optional[str] = None) -> bool:
        """Returns true if the fileset contains files.

        Args:
            fileset (str or list[str]): Fileset(s) to query. If not provided,
                the active fileset is used.
            filetype (str or list[str], optional): File type(s) to filter by
                (e.g., 'verilog'). If not provided, all filetypes in the
                fileset are returned.

        Returns:
            bool: True if the fileset contains files.
        """

        if fileset is None:
            fileset = self._get_active("fileset")

        if not isinstance(fileset, list):
            fileset = [fileset]

        if filetype and not isinstance(filetype, list):
            filetype = [filetype]

        for fs in fileset:
            if not isinstance(fs, str):
                raise ValueError("fileset key must be a string")
            if not self.has_fileset(fs):
                continue
            # handle scalar+list in argument
            if not filetype:
                filetype = self.getkeys('fileset', fs, 'file')
            # grab the files
            for ftype in filetype:
                if self.get('fileset', fs, 'file', ftype):
                    return True

        return False

    @contextlib.contextmanager
    def active_fileset(self, fileset: str):
        """
        Provides a context to temporarily set an active design fileset.

        This is useful for applying a set of configurations to a specific
        fileset without repeatedly passing its name.

        Raises:
            TypeError: If `fileset` is not a string.
            ValueError: If `fileset` is an empty string.

        Args:
            fileset (str): The name of the fileset to activate.

        Example:
            >>> with design.active_fileset("rtl"):
            ...     design.set_topmodule("top")
            # This sets the top module for the 'rtl' fileset to 'top'.
        """
        if not isinstance(fileset, str):
            raise TypeError("fileset must a string")
        if not fileset:
            raise ValueError("fileset cannot be an empty string")

        with self._active(fileset=fileset):
            yield

    def copy_fileset(self, src_fileset: str, dst_fileset: str, clobber: bool = False) -> None:
        """
        Creates a new copy of a source fileset.

        The entire configuration of the source fileset is duplicated and stored
        under the destination fileset's name.

        Args:
            src_fileset (str): The name of the source fileset to copy.
            dst_fileset (str): The name of the new destination fileset.
            clobber (bool): If True, an existing destination fileset will be
                overwritten. Defaults to False.

        Raises:
            ValueError: If the destination fileset already exists and `clobber`
                is False.
        """
        if not clobber and self.has_fileset(dst_fileset):
            raise ValueError(f"{dst_fileset} already exists")

        new_fs = self.get("fileset", src_fileset, field="schema").copy()
        EditableSchema(self).insert("fileset", dst_fileset, new_fs, clobber=True)

    def _assert_fileset(self, fileset: Union[None, Iterable[str], str]) -> None:
        """
        Raises an error if the specified fileset does not exist.

        Raises:
            TypeError: If `fileset` is not a string.
            LookupError: If the fileset is not found.
        """

        if isinstance(fileset, (list, set, tuple)):
            for fs in fileset:
                self._assert_fileset(fs)
            return

        if not isinstance(fileset, str):
            raise TypeError("fileset must be a string")

        if not self.has_fileset(fileset):
            name = getattr(self, "name", None)
            if name:
                raise LookupError(f"{fileset} is not defined in {name}")
            else:
                raise LookupError(f"{fileset} is not defined")

    def has_fileset(self, fileset: str) -> bool:
        """
        Checks if a fileset exists in the schema.

        Args:
            fileset (str): The name of the fileset to check.

        Returns:
            bool: True if the fileset exists, False otherwise.
        """

        return fileset in self.getkeys("fileset")

    def _generate_doc(self, doc,
                      ref_root: str = "",
                      key_offset: Optional[Tuple[str, ...]] = None,
                      detailed: bool = True):
        from ..schema.docs.utils import build_section

        filesets_sec = build_section("Filesets", f"{ref_root}-filesets")
        filesets_added = False
        for fileset in self.getkeys("fileset"):
            fileset_sec = build_section(fileset, f"{ref_root}-filesets-{fileset}")

            params = BaseSchema._generate_doc(self.get("fileset", fileset, field="schema"),
                                              doc,
                                              ref_root=f"{ref_root}-filesets-{fileset}",
                                              key_offset=key_offset,
                                              detailed=False)
            if not params:
                continue

            fileset_sec += params
            filesets_sec += fileset_sec
            filesets_added = True

        if filesets_added:
            return filesets_sec
        return None
