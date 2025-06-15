import os.path

from siliconcompiler.schema.baseschema import BaseSchema
from siliconcompiler.schema.editableschema import EditableSchema
from siliconcompiler.schema.parameter import Parameter, Scope
from siliconcompiler.schema.namedschema import NamedSchema
from siliconcompiler.schema.utils import trim

from siliconcompiler.package import Resolver


class DependencySchema(BaseSchema):
    '''
    Schema extension to add :meth:`.add_dep` capability to a schema section.
    '''

    def __init__(self):
        super().__init__()

        self.__deps = {}

        schema = EditableSchema(self)
        schema.insert(
            "deps",
            Parameter(
                '[str]',
                scope=Scope.GLOBAL,
                lock=True,
                shorthelp="List of dependencies",
                help="List of named object dependencies included via add_dep()."))

        schema.insert(
            'package', 'default', 'root',
            Parameter(
                'str',
                scope=Scope.GLOBAL,
                shorthelp="Package: package root",
                example=[
                    "api: chip.set('source', "
                    "'freepdk45_data', 'path', 'ssh://git@github.com/siliconcompiler/freepdk45/')"],
                help=trim("""
                    Package root path, this points the location where the package data can be
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
            'package', 'default', 'tag',
            Parameter(
                'str',
                scope=Scope.GLOBAL,
                shorthelp="Package: package tag/version",
                example=[
                    "api: chip.set('source', 'freepdk45_data', 'ref', '07ec4aa')"],
                help=trim("""
                    Package reference tag. The meaning of the this tag depends on the context of
                    the root.
                    For git, this can be a tag, branch, or commit id. For https this is the version
                    of the file that will be downloaded.
                    """)))

    def _from_dict(self, manifest, keypath, version=None):
        self.set("deps", False, field="lock")
        ret = super()._from_dict(manifest, keypath, version)
        self.set("deps", True, field="lock")
        return ret

    def add_dep(self, obj: NamedSchema, clobber: bool = True) -> bool:
        """
        Adds a module to this object.

        Args:
            obj (:class:`NamedSchema`): Module to add
            clobber (bool): If true will insert the object and overwrite any
                existing with the same name

        Returns:
            True if object was imported, otherwise false.
        """

        if not isinstance(obj, NamedSchema):
            raise TypeError(f"Cannot add an object of type: {type(obj)}")

        if not clobber and obj.name() in self.__deps:
            return False

        if obj.name() not in self.__deps:
            self.set("deps", False, field="lock")
            self.add("deps", obj.name())
            self.set("deps", True, field="lock")

        self.__deps[obj.name()] = obj
        obj._reset()

        return True

    def write_depgraph(self, filename: str,
                       fontcolor: str = '#000000',
                       background: str = 'transparent',
                       fontsize: str = '14',
                       border: bool = True, landscape: bool = False) -> None:
        r'''
        Renders and saves the dependency graph to a file.

        Args:
            filename (filepath): Output filepath
            fontcolor (str): Node font RGB color hex value
            background (str): Background color
            fontsize (str): Node text font size
            border (bool): Enables node border if True
            landscape (bool): Renders graph in landscape layout if True

        Examples:
            >>> schema.write_depgraph('mydump.png')
            Renders the object dependency graph and writes the result to a png file.
        '''
        import graphviz

        filepath = os.path.abspath(filename)
        fileroot, ext = os.path.splitext(filepath)
        fileformat = ext[1:]

        # controlling border width
        if border:
            penwidth = '1'
        else:
            penwidth = '0'

        # controlling graph direction
        if landscape:
            rankdir = 'LR'
        else:
            rankdir = 'TB'

        dot = graphviz.Digraph(format=fileformat)
        dot.graph_attr['rankdir'] = rankdir
        dot.attr(bgcolor=background)

        def make_label(dep):
            return f"lib-{dep.name()}"

        nodes = {
            self.name(): {
                "text": self.name(),
                "shape": "box",
                "color": background,
                "connects_to": set([make_label(subdep) for subdep in self.__deps.values()])
            }
        }
        for dep in self.get_dep():
            nodes[make_label(dep)] = {
                "text": dep.name(),
                "shape": "oval",
                "color": background,
                "connects_to": set([make_label(subdep) for subdep in dep.__deps.values()])
            }

        for label, info in nodes.items():
            dot.node(label, label=info['text'], bordercolor=fontcolor, style='filled',
                     fontcolor=fontcolor, fontsize=fontsize, ordering="in",
                     penwidth=penwidth, fillcolor=info["color"], shape=info['shape'])

            for conn in info['connects_to']:
                dot.edge(label, conn, dir='back')

        try:
            dot.render(filename=fileroot, cleanup=True)
        except graphviz.ExecutableNotFound as e:
            raise RuntimeError(f'Unable to save flowgraph: {e}')

    def __get_all_deps(self, seen: set) -> list:
        '''
        Loop through the dependency tree and generate a flat list
        '''
        deps = []

        for obj in self.__deps.values():
            if obj.name() in seen:
                continue

            deps.append(obj)
            seen.add(obj.name())

            if not isinstance(obj, DependencySchema):
                # nothing to iterate over
                continue

            for obj_dep in obj.__get_all_deps(seen):
                deps.append(obj_dep)
                seen.add(obj_dep.name())

        return deps

    def get_dep(self, name: str = None, hierarchy: bool = True) -> list:
        '''
        Returns all dependencies associated with this object or a specific one if requested.

        Raises:
            KeyError: if the module specific module is requested but not found

        Args:
            name (str): name of the module
            hierarchy (bool): if True, will return all modules including children
                otherwise only this objects modules are returned.
        '''

        if name:
            if name not in self.__deps:
                raise KeyError(f"{name} is not an imported module")

            return self.__deps[name]

        if hierarchy:
            return self.__get_all_deps(set())
        return list(self.__deps.values())

    def remove_dep(self, name: str) -> bool:
        '''
        Removes a previously registered module.

        Args:
            name (str): name of the module

        Returns:
            True if the module was removed, False is not found.
        '''
        if name not in self.__deps:
            return False

        del self.__deps[name]

        # Remove from dependency list
        dependencies = self.get("deps")
        dependencies.remove(name)

        self.set("deps", False, field="lock")
        self.set("deps", dependencies)
        self.set("deps", True, field="lock")

        return True

    def _populate_deps(self, module_map: dict):
        if self.__deps:
            return

        for module in self.get("deps"):
            if module not in module_map:
                raise ValueError(f"{module} not available in map")
            self.__deps[module] = module_map[module]

            if isinstance(self.__deps[module], DependencySchema):
                self.__deps[module]._populate_deps(module_map)

    def register_package(self, name: str, root: str, tag: str = None):
        """
        Registers a package by its name with the root and associated tag.

        Args:
            name (str): Package name
            root (str): Path to the root, can be directory, git url, or archive url
            tag (str): Reference of the sources, can be commitid, branch name, tag

        Examples:
            >>> schema.register_package('siliconcompiler_data',
                    'git+https://github.com/siliconcompiler/siliconcompiler',
                    'v1.0.0')
        """

        if os.path.isfile(root):
            root = os.path.dirname(os.path.abspath(root))

        self.set("package", name, "root", root)
        if tag:
            self.set("package", name, "tag", tag)

    def find_package(self, name: str):
        """
        Returns absolute path to the package root.

        Raises:
            ValueError: is package is not found

        Args:
            name (str): name of the package to find.

        Returns:
            Path to the package directory root.

        Examples:
            >>> schema.find_package('siliconcompiler')
            Returns the path to the root of the siliconcompiler package.
        """

        if not self.valid("package", name):
            raise ValueError(f"{name} is not a recognized source")

        root = self.get("package", name, "root")
        tag = self.get("package", name, "tag")

        resolver = Resolver.find_resolver(root)
        return resolver(name, self._parent(root=True), root, tag).get_path()

    def __get_resolver_map(self):
        """
        Generate the resolver map got package handling for find_files and check_filepaths
        """
        schema_root = self._parent(root=True)
        resolver_map = {}
        for package in self.getkeys("package"):
            root = self.get("package", package, "root")
            tag = self.get("package", package, "tag")
            resolver = Resolver.find_resolver(root)
            resolver_map[package] = resolver(package, schema_root, root, tag).get_path
        return resolver_map

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
                                  packages=self.__get_resolver_map(),
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
        logger = getattr(schema_root, "logger", None)
        collection_dir = getattr(schema_root, "collection_dir", None)
        if collection_dir:
            collection_dir = collection_dir()

        return super().check_filepaths(
            ignore_keys=ignore_keys,
            logger=logger,
            packages=self.__get_resolver_map(),
            collection_dir=collection_dir,
            cwd=cwd)
