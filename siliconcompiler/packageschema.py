import os

import os.path

from siliconcompiler.schema import BaseSchema
from siliconcompiler.schema import EditableSchema, Parameter, Scope
from siliconcompiler.schema.utils import trim
from siliconcompiler.package import Resolver


class PackageSchema(BaseSchema):
    def __init__(self):
        super().__init__()

        schema_package(self)

        self.__cache = {}

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
        resolver.set_cache(self.__cache)
        return resolver

    def get_resolvers(self):
        '''
        Returns a dictionary of packages with their resolver method.
        '''
        resolvers = {}
        for package in self.getkeys("source"):
            resolvers[package] = self.get_resolver(package).get_path

        return resolvers

    def _set_cache(self, package, path):
        self.__cache[package] = path

    def get_path_cache(self):
        return self.__cache.copy()


############################################
# Package information
############################################
def schema_package(schema):
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
