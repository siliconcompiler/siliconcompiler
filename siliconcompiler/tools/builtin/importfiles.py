import shutil

import os.path

from pathlib import Path

from typing import Union, List, Optional

from siliconcompiler import Task
from siliconcompiler.utils import link_copy


class ImportFilesTask(Task):
    '''A built-in task to import (copy) files and directories.

    This task provides a mechanism to copy specified files and directories
    from their source locations into the current task's output directory
    (``outputs/``), making them available for subsequent steps in the tool flow.
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("file", "[file]", "input files to import")
        self.add_parameter("dir", "[dir]", "input directories to import")

    def add_import_file(self, file: Union[List[Union[str, Path]], str, Path],
                        dataroot: Optional[str] = None,
                        step: Optional[str] = None, index: Optional[str] = None,
                        clobber: bool = False) -> None:
        """Adds one or more files to the list of items to import.

        Args:
            file (Union[List[Union[str, Path]], str, Path]): The path(s) to the file(s)
                to be imported.
            dataroot (Optional[str]): The dataroot to use for resolving relative paths.
                If None, the active dataroot is used. Defaults to None.
            step (Optional[str]): The step to associate this file with.
                Defaults to the current step.
            index (Optional[str]): The index to associate this file with.
                Defaults to the current index.
            clobber (bool): If True, existing file entries for the specified
                step/index will be overwritten. If False, the new file(s)
                will be appended. Defaults to False.
        """
        with self.active_dataroot(self._get_active_dataroot(dataroot)):
            if clobber:
                self.set("var", "file", file, step=step, index=index)
            else:
                self.add("var", "file", file, step=step, index=index)

    def add_import_dir(self, directory: Union[List[Union[str, Path]], str, Path],
                       dataroot: Optional[str] = None,
                       step: Optional[str] = None, index: Optional[str] = None,
                       clobber: bool = False) -> None:
        """Adds one or more directories to the list of items to import.

        Args:
            directory (Union[List[Union[str, Path]], str, Path]): The path(s) to the
                directory/directories to be imported.
            dataroot (Optional[str]): The dataroot to use for resolving relative paths.
                If None, the active dataroot is used. Defaults to None.
            step (Optional[str]): The step to associate this directory with.
                Defaults to the current step.
            index (Optional[str]): The index to associate this directory with.
                Defaults to the current index.
            clobber (bool): If True, existing directory entries for the specified
                step/index will be overwritten. If False, the new directory/directories
                will be appended. Defaults to False.
        """
        with self.active_dataroot(self._get_active_dataroot(dataroot)):
            if clobber:
                self.set("var", "dir", directory, step=step, index=index)
            else:
                self.add("var", "dir", directory, step=step, index=index)

    def tool(self) -> str:
        return "builtin"

    def task(self) -> str:
        return "importfiles"

    def setup(self) -> None:
        """Prepares the task for execution by setting up dependencies and requirements.

        This method validates that the task is configured correctly (i.e., has files
        or directories to import and does not have formal input nodes) and registers
        the items to be imported as task outputs.

        Raises:
            ValueError: If the task is configured with input nodes or if no
                files or directories are specified for import.
        """
        super().setup()

        self.set_threads(1)

        if (self.step, self.index) not in self.schema_flow.get_entry_nodes():
            raise ValueError("task must be an entry node")

        if not self.get("var", "file") and not self.get("var", "dir"):
            raise ValueError("task requires files or directories to import")

        if self.get("var", "file"):
            self.add_required_key("var", "file")

        if self.get("var", "dir"):
            self.add_required_key("var", "dir")

        for file in self.get("var", "file") + self.get("var", "dir"):
            self.add_output_file(os.path.basename(file))

    def run(self) -> int:
        """Executes the file and directory import process.

        Copies all specified files and directories into the task's ``outputs/``
        directory using a copy function that attempts to create hard links
        as an optimization.

        Returns:
            int: A status code, where 0 indicates successful execution.
        """
        self.logger.info(f"Running builtin task '{self.task()}'")

        for file in self.find_files("var", "file"):
            self.logger.debug(f"Copying file {file} to outputs")
            link_copy(file, "outputs/")

        for directory in self.find_files("var", "dir"):
            # For directories, copytree needs the destination to be the specific new directory name
            dest_dir = os.path.join("outputs", os.path.basename(directory))
            self.logger.debug(f"Copying directory {directory} to {dest_dir}")
            shutil.copytree(directory, dest_dir, copy_function=link_copy)

        return 0

    @classmethod
    def make_docs(cls):
        from siliconcompiler import Flowgraph, Design, Project
        from siliconcompiler.scheduler import SchedulerNode
        design = Design("<design>")
        with design.active_fileset("docs"):
            design.set_topmodule("top")
        proj = Project(design)
        proj.add_fileset("docs")
        flow = Flowgraph("docsflow")
        flow.node("<step>", cls(), index="<index>")
        proj.set_flow(flow)

        cls.find_task(proj).add_import_file("import.txt")
        cls.find_task(proj).add_import_dir("/directory")

        node = SchedulerNode(proj, "<step>", "<index>")
        node.setup()
        return node.task
