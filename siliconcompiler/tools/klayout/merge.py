from typing import Optional, Union

from siliconcompiler.tools.klayout import KLayoutTask


class Merge(KLayoutTask):
    """
    Klayout task to merge multiple GDS files and provide prefixing for cell names.
    """
    def __init__(self):
        super().__init__()

        self.add_parameter("reference", "(<fs,input>,str,str)",
                           "Reference fileset or input node for merge operation, structured as "
                           "(fs, library name, fileset) or (input, step, index)")
        self.add_parameter("merge", "[(<fs,input>,str,str,str)]",
                           "Fileset or input node to be merge with prefix, structured as "
                           "(fs, library name, fileset) or (input, step, index) along with prefix "
                           "string")

    def __fix_type(self, type: str) -> str:
        if type == "fileset":
            return "fs"
        return type

    def set_klayout_reference(self, type: str, source0: str, source1: str,
                              step: Optional[str] = None,
                              index: Optional[Union[str, int]] = None):
        """
        Sets the reference file for the merge operation.
        Args:
            type (str): The reference fileset or input node.
            source0 (str): The first part of the source (library name or step).
            source1 (str): The second part of the source (fileset name or index).
            step (Optional[str]): The specific step to apply this configuration to.
            index (Optional[Union[str, int]]): The specific index to apply this configuration to.
        """
        self.set("var", "reference", (self.__fix_type(type), source0, source1),
                 step=step, index=index)

    def add_klayout_merge(self, type: str, source0: str, source1: str, prefix: str,
                          step: Optional[str] = None,
                          index: Optional[Union[str, int]] = None, clobber: bool = False):
        """
        Adds a file to be merged with the reference file.
        Args:
            type (str): The fileset or input node to be merged.
            prefix (str): The prefix to apply during the merge.
            source0 (str): The first part of the source (library name or step).
            source1 (str): The second part of the source (fileset name or index).
            step (Optional[str]): The specific step to apply this configuration to.
            index (Optional[Union[str, int]]): The specific index to apply this configuration to.
            clobber (bool, optional): If True, overwrites the existing list of merge files.
                                      If False, appends to the list. Defaults to False.
        """
        if clobber:
            self.set("var", "merge", (self.__fix_type(type), source0, source1, prefix),
                     step=step, index=index)
        else:
            self.add("var", "merge", (self.__fix_type(type), source0, source1, prefix),
                     step=step, index=index)

    def task(self) -> str:
        return 'merge'

    def setup(self) -> None:
        super().setup()

        self.set_script("klayout_merge.py")

        self.add_required_key("var", "reference")
        self.add_required_key("var", "merge")

        if self.get("var", "reference"):
            ref_type, ref_source0, ref_source1 = self.get("var", "reference")
            if ref_type == 'input':
                step, index = ref_source0, ref_source1
                self.add_input_file(
                    self.compute_input_file_node_name(f"{self.design_topmodule}.gds",
                                                      step, index))
            else:
                lib_name, fileset = ref_source0, ref_source1
                self.add_required_key("library", lib_name, "fileset", fileset, "file", "gds")
        for merge_entry in self.get("var", "merge"):
            merge_type, merge_source0, merge_source1, _ = merge_entry
            if merge_type == 'input':
                step, index = merge_source0, merge_source1
                self.add_input_file(
                    self.compute_input_file_node_name(f"{self.design_topmodule}.gds",
                                                      step, index))
            else:
                lib_name, fileset = merge_source0, merge_source1
                self.add_required_key("library", lib_name, "fileset", fileset, "file", "gds")

        self.add_output_file(ext="gds")
