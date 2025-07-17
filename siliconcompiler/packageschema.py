import os

import os.path

from typing import Union, Dict, List

from siliconcompiler.pathschema import PathSchema
from siliconcompiler.schema import BaseSchema, EditableSchema, Parameter, Scope
from siliconcompiler.schema.utils import trim
from siliconcompiler.package import Resolver


class PackageSchema(PathSchema):
    def __init__(self):
        super().__init__()

        schema_package(self)

    def set_description(self, desc: str):
        """
        Set the description of the package.

        Args:
            desc (str): The description string.
        """
        return self.set("package", "description", trim(desc))

    def get_description(self) -> str:
        """Get the description of the package.

        Returns:
            str: The description string.
        """
        return self.get("package", "description")

    def set_version(self, version: str):
        """
        Set the version of the package.

        Args:
            version (str): The version string.
        """
        return self.set("package", "version", version)

    def get_version(self) -> str:
        """
        Get the version of the package.

        Returns:
            str: The version string.
        """
        return self.get("package", "version")

    def add_license(self, name: str):
        """
        Add a license name to the package.

        Args:
            name (str): The name of the license.
        """
        return self.add("package", "license", name)

    def add_license_file(self, file: str, dataroot: str = None):
        """
        Add a license file to the package.

        Args:
            file (str): The path to the license file.
            dataroot (str, optional): The data reference for the package. Defaults to None,
                                    which uses the active package.
        """
        if not dataroot:
            dataroot = self._get_active("package")
        with self.active_dataroot(dataroot):
            return self.add("package", "licensefile", file)

    def get_licenses(self) -> List[str]:
        """
        Get a list of license names associated with the package.
        """
        return self.get("package", "license")

    def get_license_files(self) -> List[str]:
        """
        Get a list of license file paths associated with the package.
        """
        return self.find_files("package", "licensefile")

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
            params.append(self.set("package", "author", identifier, "name", name))
        if email:
            params.append(self.set("package", "author", identifier, "email", email))
        if organization:
            params.append(self.set("package", "author", identifier, "organization", organization))
        return [p for p in params if p]

    def add_documentation(self, type: str, path: str, dataroot: str = None):
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
        if not dataroot:
            dataroot = self._get_active("package")
        with self.active_dataroot(dataroot):
            return self.add("package", "doc", type, path)

    def get_documentation(self, type: str = None) -> Union[List[str], Dict[str, List[str]]]:
        """
        Get documentation files for the package.

        Args:
            type (str, optional): The type of documentation to retrieve. If None,
                                returns all documentation organized by type. Defaults to None.
        """
        if type:
            return self.find_files("package", "doc", type)

        docs = {}
        for type in self.getkeys("package", "doc"):
            doc_files = self.find_files("package", "doc", type)
            if doc_files:
                docs[type] = doc_files
        return docs


############################################
# Package information
############################################
def schema_package(schema):
    schema = EditableSchema(schema)

    schema.insert(
        'package', 'version',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Package: version",
            switch="-package_version <str>",
            example=[
                "cli: -package_version 1.0",
                "api: chip.set('package', 'version', '1.0')"],
            help=trim("""Package version. Can be a branch, tag, commit hash,
            or a semver compatible version.""")))

    schema.insert(
        'package', 'description',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Package: description",
            switch="-package_description <str>",
            example=[
                "cli: -package_description 'Yet another cpu'",
                "api: chip.set('package', 'description', 'Yet another cpu')"],
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
            'package', 'doc', item,
            Parameter(
                '[file]',
                scope=Scope.GLOBAL,
                shorthelp=f"Package: {item} document",
                switch=f"-package_doc_{item} <file>",
                example=[
                    f"cli: -package_doc_{item} {item}.pdf",
                    f"api: chip.set('package', 'doc', '{item}', '{item}.pdf')"],
                help=trim(f"""Package list of {item} documents.""")))

    schema.insert(
        'package', 'license',
        Parameter(
            '[str]',
            scope=Scope.GLOBAL,
            shorthelp="Package: license identifiers",
            switch="-package_license <str>",
            example=[
                "cli: -package_license 'Apache-2.0'",
                "api: chip.set('package', 'license', 'Apache-2.0')"],
            help=trim("""Package list of SPDX license identifiers.""")))

    schema.insert(
        'package', 'licensefile',
        Parameter(
            '[file]',
            scope=Scope.GLOBAL,
            shorthelp="Package: license files",
            switch="-package_licensefile <file>",
            example=[
                "cli: -package_licensefile './LICENSE'",
                "api: chip.set('package', 'licensefile', './LICENSE')"],
            help=trim("""Package list of license files for to be
            applied in cases when a SPDX identifier is not available.
            (eg. proprietary licenses).""")))

    for item in [
            'name',
            'email',
            'organization']:
        schema.insert(
            'package', 'author', 'default', item,
            Parameter(
                'str',
                scope=Scope.GLOBAL,
                shorthelp=f"Package: author {item}",
                switch=f"-package_author_{item} 'userid <str>'",
                example=[
                    f"cli: -package_author_{item} 'wiley wiley@acme.com'",
                    f"api: chip.set('package', 'author', 'wiley', '{item}', 'wiley@acme.com')"],
                help=trim(f"""Package author {item} provided with full name as key and
                {item} as value.""")))


class PackageSchemaTmp(BaseSchema):
    def __init__(self):
        super().__init__()

        schema_package_tmp(self)

    def register(self, name, path, ref=None, clobber=True):
        """
        Registers a package by its name with the source path and reference

        Registered package sources are stored in the package section of the schema.

        Args:
            name (str): Package name
            path (str): Path to the sources, can be file, git url, archive url
            ref (str): Reference of the sources, can be commitid, branch name, tag
            clobber (bool): Overwrite existing

        Examples:
            >>> schema.register('siliconcompiler_data',
                    'git+https://github.com/siliconcompiler/siliconcompiler',
                    'cd328131bafd361787f9137a6ffed999d64c8c30')
        """

        # If this is a file, get the directory for this
        if os.path.isfile(path):
            path = os.path.dirname(os.path.abspath(path))
        elif os.path.isdir(path):
            path = os.path.abspath(path)

        success = False
        if self.set('source', name, 'path', path, clobber=clobber):
            success = True
        if success and ref:
            success = False
            if self.set('source', name, 'ref', ref, clobber=clobber):
                success = True
        return success

    def get_resolver(self, package):
        '''
        Returns a specific resolver

        Args:
            package (str): name of package
        '''
        resolver_cls = Resolver.find_resolver(self.get("source", package, "path"))
        resolver = resolver_cls(package, self._parent(root=True),
                                self.get("source", package, "path"),
                                self.get("source", package, "ref"))
        return resolver

    def get_resolvers(self):
        '''
        Returns a dictionary of packages with their resolver method.
        '''
        resolvers = {}
        for package in self.getkeys("source"):
            resolvers[package] = self.get_resolver(package).get_path

        return resolvers


############################################
# Package information
############################################
def schema_package_tmp(schema):
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
                "api: chip.set('package', 'version', '1.0')"],
            help=trim("""Package version. Can be a branch, tag, commit hash,
            or a semver compatible version.""")))

    schema.insert(
        'description',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Package: description",
            switch="-package_description <str>",
            example=[
                "cli: -package_description 'Yet another cpu'",
                "api: chip.set('package', 'description', 'Yet another cpu')"],
            help=trim("""Package short one line description for package
            managers and summary reports.""")))

    schema.insert(
        'keyword',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Package: keyword",
            switch="-package_keyword <str>",
            example=[
                "cli: -package_keyword cpu",
                "api: chip.set('package', 'keyword', 'cpu')"],
            help=trim("""Package keyword(s) used to characterize package.""")))
    schema.insert(
        'doc', 'homepage',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Package: documentation homepage",
            switch="-package_doc_homepage <str>",
            example=[
                "cli: -package_doc_homepage index.html",
                "api: chip.set('package', 'doc', 'homepage', 'index.html')"],
            help=trim("""
            Package documentation homepage. Filepath to design docs homepage.
            Complex designs can can include a long non standard list of
            documents dependent. A single html entry point can be used to
            present an organized documentation dashboard to the designer.""")))

    doctypes = ['datasheet',
                'reference',
                'userguide',
                'quickstart',
                'releasenotes',
                'testplan',
                'signoff',
                'tutorial']

    for item in doctypes:
        schema.insert(
            'doc', item,
            Parameter(
                '[file]',
                scope=Scope.GLOBAL,
                shorthelp=f"Package: {item} document",
                switch=f"-package_doc_{item} <file>",
                example=[
                    f"cli: -package_doc_{item} {item}.pdf",
                    f"api: chip.set('package', 'doc', '{item}', '{item}.pdf')"],
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
                "api: chip.set('package', 'license', 'Apache-2.0')"],
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
                "api: chip.set('package', 'licensefile', './LICENSE')"],
            help=trim("""Package list of license files for to be
            applied in cases when a SPDX identifier is not available.
            (eg. proprietary licenses).""")))

    schema.insert(
        'organization',
        Parameter(
            '[str]',
            scope=Scope.GLOBAL,
            shorthelp="Package: sponsoring organization",
            switch="-package_organization <str>",
            example=[
                "cli: -package_organization 'humanity'",
                "api: chip.set('package', 'organization', 'humanity')"],
            help=trim("""Package sponsoring organization. The field can be left
            blank if not applicable.""")))

    record = ['name',
              'email',
              'username',
              'location',
              'organization',
              'publickey']

    for item in record:
        schema.insert(
            'author', 'default', item,
            Parameter(
                'str',
                scope=Scope.GLOBAL,
                shorthelp=f"Package: author {item}",
                switch=f"-package_author_{item} 'userid <str>'",
                example=[
                    f"cli: -package_author_{item} 'wiley wiley@acme.com'",
                    f"api: chip.set('package', 'author', 'wiley', '{item}', 'wiley@acme.com')"],
                help=trim(f"""Package author {item} provided with full name as key and
                {item} as value.""")))

    schema.insert(
        'source', 'default', 'path',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Package: data source path",
            switch="-package_source_path 'source <str>'",
            example=[
                "cli: -package_source_path "
                "'freepdk45_data ssh://git@github.com/siliconcompiler/freepdk45/'",
                "api: chip.set('package', 'source', "
                "'freepdk45_data', 'path', 'ssh://git@github.com/siliconcompiler/freepdk45/')"],
            help=trim("""
            Package data source path, allowed paths:

            * /path/on/network/drive
            * file:///path/on/network/drive
            * git+https://github.com/xyz/xyz
            * git://github.com/xyz/xyz
            * git+ssh://github.com/xyz/xyz
            * ssh://github.com/xyz/xyz
            * https://github.com/xyz/xyz/archive
            * https://zeroasic.com/xyz.tar.gz
            * python://siliconcompiler
            """)))

    schema.insert(
        'source', 'default', 'ref',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Package: data source reference",
            switch="-package_source_ref 'source <str>'",
            example=[
                "cli: -package_source_ref 'freepdk45_data 07ec4aa'",
                "api: chip.set('package', 'source', 'freepdk45_data', 'ref', '07ec4aa')"],
            help=trim("""Package data source reference""")))
