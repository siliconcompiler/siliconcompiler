from typing import Union, Dict, List, Tuple, Optional

from siliconcompiler.schema_support.pathschema import PathSchema
from siliconcompiler.schema import EditableSchema, Parameter, Scope, BaseSchema
from siliconcompiler.schema.utils import trim


class PackageSchema(PathSchema):
    """
    A class for managing package-related schema data.
    """
    def __init__(self):
        """
        Initializes a PackageSchema object.
        """
        super().__init__()

        schema_package(self)

    def set_description(self, desc: str):
        """
        Set the description of the package.

        Args:
            desc (str): The description string.
        """
        return self.set("description", trim(desc))

    def get_description(self) -> str:
        """
        Get the description of the package.

        Returns:
            str: The description string.
        """

        return self.get("description")

    def set_version(self, version: str):
        """
        Set the version of the package.

        Args:
            version (str): The version string.
        """
        return self.set("version", version)

    def get_version(self) -> str:
        """
        Get the version of the package.

        Returns:
            str: The version string.
        """
        return self.get("version")

    def set_vendor(self, vendor: str):
        """
        Set the vendor of the package.

        Args:
            vendor (str): The vendor name.
        """
        return self.set("vendor", vendor)

    def get_vendor(self) -> str:
        """
        Get the vendor of the package.

        Returns:
            str: The vendor name.
        """
        return self.get("vendor")

    def add_license(self, name: str):
        """
        Add a license name to the package.

        Args:
            name (str): The name of the license.
        """
        return self.add("license", name)

    def add_licensefile(self, file: str, dataroot: str = None):
        """
        Add a license file to the package.

        Args:
            file (str): The path to the license file.
            dataroot (str, optional): The data reference for the package. Defaults to None,
                                    which uses the active package.
        """
        with self.active_dataroot(self._get_active_dataroot(dataroot)):
            return self.add("licensefile", file)

    def get_license(self) -> List[str]:
        """
        Get a list of license names associated with the package.

        Returns:
            List[str]: A list of license names.
        """
        return self.get("license")

    def get_licensefile(self) -> List[str]:
        """
        Get a list of license file paths associated with the package.

        Returns:
            List[str]: A list of file paths.
        """
        return self.find_files("licensefile")

    def add_author(self,
                   identifier: str,
                   name: str = None,
                   email: str = None,
                   organization: str = None):
        """
        Add or update author information for the package.

        Args:
            identifier (str): A unique identifier for the author.
            name (str, optional): The author's name. Defaults to None.
            email (str, optional): The author's email address. Defaults to None.
            organization (str, optional): The author's organization. Defaults to None.
        """
        params = []
        if name:
            params.append(self.set("author", identifier, "name", name))
        if email:
            params.append(self.set("author", identifier, "email", email))
        if organization:
            params.append(self.set("author", identifier, "organization", organization))
        return [p for p in params if p]

    def get_author(self, identifier: str = None):
        """
        Returns the author information for a specific author or all authors.

        Args:
            identifier (str): A unique identifier for the author, if None returns all
        """
        if identifier is None:
            authors = []
            for author in self.getkeys("author"):
                authors.append(self.get_author(author))
            return authors
        return {
            "name": self.get("author", identifier, "name"),
            "email": self.get("author", identifier, "email"),
            "organization": self.get("author", identifier, "organization")
        }

    def add_doc(self, type: str, path: str, dataroot: str = None):
        """
        Add documentation to the package.

        Args:
            type (str): The type of documentation (e.g., "manual", "api").
            path (str): The path to the documentation file.
            dataroot (str, optional): The data reference for the package. Defaults to None,
                                    which uses the active package.

        Returns:
            The result of the `add` operation.
        """
        with self.active_dataroot(self._get_active_dataroot(dataroot)):
            return self.add("doc", type, path)

    def get_doc(self, type: str = None) -> Union[List[str], Dict[str, List[str]]]:
        """
        Get documentation files for the package.

        Args:
            type (str, optional): The type of documentation to retrieve. If None,
                                returns all documentation organized by type. Defaults to None.
        """
        if type:
            return self.find_files("doc", type)

        docs = {}
        for type in self.getkeys("doc"):
            doc_files = self.find_files("doc", type)
            if doc_files:
                docs[type] = doc_files
        return docs

    @classmethod
    def _getdict_type(cls) -> str:
        """
        Returns the meta data for getdict
        """

        return PackageSchema.__name__

    def _generate_doc(self, doc,
                      ref_root: str = "",
                      key_offset: Optional[Tuple[str, ...]] = None,
                      detailed: bool = True):
        from ..schema.docs.utils import build_section
        section = build_section("Package", f"{ref_root}-package")
        params = BaseSchema._generate_doc(self,
                                          doc,
                                          ref_root=f"{ref_root}-package",
                                          key_offset=key_offset,
                                          detailed=False)
        if not params:
            return None

        section += params
        return section


############################################
# Package information
############################################
def schema_package(schema):
    """
    Adds package schema parameters to the given schema.

    Args:
        schema (EditableSchema): The schema to modify.
    """
    schema = EditableSchema(schema)

    schema.insert(
        'version',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Package: version",
            switch="-package_version <str>",
            example=[
                "cli: -package_version 1.0",
                "api: schema.set('version', '1.0')"],
            help=trim("""Package version. Can be a branch, tag, commit hash,
            or a semver compatible version.""")))

    schema.insert(
        'vendor',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Package: vendor",
            switch="-package_vendor <str>",
            example=[
                "cli: -package_vendor acme",
                "api: schema.set('vendor', 'acme')"],
            help=trim("""Package vendor.""")))

    schema.insert(
        'description',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Package: description",
            switch="-package_description <str>",
            example=[
                "cli: -package_description 'Yet another cpu'",
                "api: schema.set('description', 'Yet another cpu')"],
            help=trim("""Package short one line description for package
            managers and summary reports.""")))

    for item in [
            'datasheet',
            'reference',
            'userguide',
            'quickstart',
            'releasenotes',
            'testplan',
            'signoff',
            'tutorial']:
        schema.insert(
            'doc', item,
            Parameter(
                '[file]',
                scope=Scope.GLOBAL,
                shorthelp=f"Package: {item} document",
                switch=f"-package_doc_{item} <file>",
                example=[
                    f"cli: -package_doc_{item} {item}.pdf",
                    f"api: schema.set('doc', '{item}', '{item}.pdf')"],
                help=trim(f"""Package list of {item} documents.""")))

    schema.insert(
        'license',
        Parameter(
            '[str]',
            scope=Scope.GLOBAL,
            shorthelp="Package: license identifiers",
            switch="-package_license <str>",
            example=[
                "cli: -package_license 'Apache-2.0'",
                "api: schema.set('license', 'Apache-2.0')"],
            help=trim("""Package list of SPDX license identifiers.""")))

    schema.insert(
        'licensefile',
        Parameter(
            '[file]',
            scope=Scope.GLOBAL,
            shorthelp="Package: license files",
            switch="-package_licensefile <file>",
            example=[
                "cli: -package_licensefile './LICENSE'",
                "api: schema.set('licensefile', './LICENSE')"],
            help=trim("""Package list of license files for to be
            applied in cases when a SPDX identifier is not available.
            (eg. proprietary licenses).""")))

    for item in [
            'name',
            'email',
            'organization']:
        schema.insert(
            'author', 'default', item,
            Parameter(
                'str',
                scope=Scope.GLOBAL,
                shorthelp=f"Package: author {item}",
                switch=f"-package_author_{item} 'userid <str>'",
                example=[
                    f"cli: -package_author_{item} 'wiley wiley@acme.com'",
                    f"api: schema.set('author', 'wiley', '{item}', 'wiley@acme.com')"],
                help=trim(f"""Package author {item} provided with full name as key and
                {item} as value.""")))
