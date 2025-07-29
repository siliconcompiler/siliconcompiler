import contextlib

from typing import List

from siliconcompiler import utils

from siliconcompiler.pathschema import PathSchema
from siliconcompiler.schema import EditableSchema, Parameter, Scope
from siliconcompiler.schema.utils import trim


###########################################################################
class FileSetSchema(PathSchema):
    def __init__(self):
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
                    "api: chip.set('fileset', 'rtl', 'file', 'verilog', 'mytop.v')",
                    "api: chip.set('fileset', 'testbench', 'file', 'verilog', 'tb.v')"],
                help=trim("""
                List of files grouped as a named set ('fileset'). The exact names of
                filetypes and filesets must match the names used in tasks
                called during flowgraph execution. The files are processed in
                the order specified by the ordered file list.""")))

    ###############################################
    def add_file(self,
                 filename: str,
                 fileset: str = None,
                 filetype: str = None,
                 clobber: bool = False,
                 dataroot: str = None) -> List[str]:
        """
        Adds files to a fileset.

        .v        → (source, verilog)
        .vhd      → (source, vhdl)
        .sdc      → (constraint, sdc)
        .lef      → (input, lef)
        .def      → (input, def)
        ...       → etc.

        Args:
            filename (Path or list[Path]): File path or list of paths to add.
            fileset (str): Logical group to associate the file with.
            filetype (str, optional): Type of the file (e.g., 'verilog', 'sdc').
            clobber (bool, optional): Clears list before adding item
            dataroot (str, optional): Data directory reference name

        Raises:
            SiliconCompilerError: If fileset or filetype cannot be inferred from
            the file extension.

        Returns:
           list[str]: List of file paths.

        Notes:
           - This method normalizes `filename` to a string for consistency.

           - If no filetype is specified, filetype is inferred based on
                the file extension via a mapping table. (eg. .v is verilog).
        """

        if fileset is None:
            fileset = self._get_active("fileset")

        if not isinstance(fileset, str):
            raise ValueError("fileset key must be a string")

        # handle list inputs
        if isinstance(filename, (list, tuple)):
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
            iomap = utils.get_default_iomap()
            if ext in iomap:
                _, default_filetype = iomap[ext]
                filetype = default_filetype
            else:
                raise ValueError(f"Unrecognized file extension: {ext}")

        if not dataroot:
            dataroot = self._get_active("package")

        # adding files to dictionary
        with self.active_dataroot(dataroot):
            if clobber:
                return self.set('fileset', fileset, 'file', filetype, filename)
            else:
                return self.add('fileset', fileset, 'file', filetype, filename)

    ###############################################
    def get_file(self,
                 fileset: str = None,
                 filetype: str = None):
        """Returns a list of files from one or more filesets.

        Args:
            fileset (str or list[str]): Fileset(s) to query.
            filetype (str or list[str], optional): File type(s) to filter by (e.g., 'verilog').

        Returns:
            list[str]: List of file paths.
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

    @contextlib.contextmanager
    def active_fileset(self, fileset: str):
        """
        Use this context to temporarily set a design fileset.

        Raises:
            TypeError: if fileset is not a string
            ValueError: if fileset if an empty string

        Args:
            fileset (str): name of the fileset

        Example:
            >>> with design.active_fileset("rtl"):
            ...     design.set_topmodule("top")
            Sets the top module for the rtl fileset as top.
        """
        if not isinstance(fileset, str):
            raise TypeError("fileset must a string")
        if not fileset:
            raise ValueError("fileset cannot be an empty string")

        with self._active(fileset=fileset):
            yield

    def copy_fileset(self, src_fileset: str, dst_fileset: str, clobber: bool = False):
        """
        Create a new copy of a source fileset and store it in the destination fileset

        Args:
            src_fileset (str): source fileset
            dst_fileset (str): destination fileset
            clobber (bool): overwrite existing fileset
        """
        if not clobber and self.has_fileset(dst_fileset):
            raise ValueError(f"{dst_fileset} already exists")

        new_fs = self.get("fileset", src_fileset, field="schema").copy()
        EditableSchema(self).insert("fileset", dst_fileset, new_fs, clobber=True)

    def _assert_fileset(self, fileset: str) -> None:
        """
        Raises an error if the fileset does not exist

        Raises:
            LookupError: if fileset is not found
        """

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
        Returns true if the fileset exists
        """

        return fileset in self.getkeys("fileset")
