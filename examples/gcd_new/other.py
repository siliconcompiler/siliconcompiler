from lambdapdk import __version__ as lambda_version
from siliconcompiler.package import PythonPathResolver

from siliconcompiler.library import StdCellLibrarySchema, YosysStdCellLibbrarySchema

from siliconcompiler import PDKSchema
from siliconcompiler.dependencyschema import DependencySchema


class FreePDK45(PDKSchema, DependencySchema):
    def __init__(self):
        super().__init__()
        self.set_name("freepdk45")

        PythonPathResolver.register_source(
            self,
            "lambdapdk",
            "lambdapdk",
            "https://github.com/siliconcompiler/lambdapdk/archive/refs/tags/",
            alternative_ref=f"v{lambda_version}",
            python_module_path_append=".."
        )


class Nangate45(StdCellLibrarySchema, YosysStdCellLibbrarySchema):
    def __init__(self):
        super().__init__()
        self.set_name("nangate45")


if __name__ == "__main__":
    p = FreePDK45()
    p.write_manifest("test.json")
