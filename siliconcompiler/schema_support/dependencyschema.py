import os.path

from typing import Dict, Union, Tuple, List, Optional, Set

from siliconcompiler.schema.baseschema import BaseSchema, LazyLoad
from siliconcompiler.schema.editableschema import EditableSchema
from siliconcompiler.schema.parameter import Parameter, Scope
from siliconcompiler.schema.namedschema import NamedSchema

from siliconcompiler.schema_support.pathschema import PathSchemaBase


class DependencySchema(BaseSchema):
    '''
    Schema extension to add :meth:`.add_dep` capability to a schema section.
    '''

    def __init__(self):
        '''Initializes the DependencySchema.'''
        super().__init__()

        self._reset_deps()

        schema = EditableSchema(self)
        schema.insert(
            "deps",
            Parameter(
                '[str]',
                scope=Scope.GLOBAL,
                lock=True,
                shorthelp="List of object dependencies",
                help="List of named object dependencies included via add_dep()."))

    def _from_dict(self, manifest: Dict,
                   keypath: Union[List[str], Tuple[str, ...]],
                   version: Optional[Tuple[int, ...]] = None,
                   lazyload: LazyLoad = LazyLoad.ON) \
            -> Tuple[Set[Tuple[str, ...]], Set[Tuple[str, ...]]]:
        '''
        Internal helper to load schema from a dictionary manifest.

        This method temporarily unlocks the 'deps' parameter to allow it to be
        populated from the manifest data.

        Args:
            manifest (dict): The dictionary to load data from.
            keypath (list): The list of keys representing the path to the data.
            version (str, optional): The schema version. Defaults to None.

        Returns:
            The result of the parent class's _from_dict method.
        '''
        self.set("deps", False, field="lock")
        ret = super()._from_dict(manifest, keypath, version=version, lazyload=lazyload)
        self.set("deps", True, field="lock")
        return ret

    def add_dep(self, obj: NamedSchema, clobber: bool = True) -> bool:
        """
        Adds a module to this object.

        Args:
            obj (:class:`NamedSchema`): Module to add.
            clobber (bool): If true will insert the object and overwrite any
                existing with the same name.

        Returns:
            True if object was imported, otherwise false.
        """

        if not isinstance(obj, NamedSchema):
            raise TypeError(f"Cannot add an object of type: {type(obj)}")

        if not clobber and obj.name in self.__deps:
            return False

        if obj.name is None:
            raise ValueError("Cannot add an unnamed dependency")

        if not self.has_dep(obj):
            self.set("deps", False, field="lock")
            self.add("deps", obj.name)
            self.set("deps", True, field="lock")

        self.__deps[obj.name] = obj

        return True

    def write_depgraph(self, filename: str,
                       fontcolor: str = '#000000',
                       background: str = 'transparent',
                       fontsize: str = '14',
                       border: bool = True, landscape: bool = False) -> None:
        r'''
        Renders and saves the dependency graph to a file.

        Args:
            filename (filepath): Output filepath.
            fontcolor (str): Node font RGB color hex value.
            background (str): Background color.
            fontsize (str): Node text font size.
            border (bool): Enables node border if True.
            landscape (bool): Renders graph in landscape layout if True.

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
            return f"lib-{dep.name}"

        nodes = {
            self.name: {
                "text": self.name,
                "shape": "box",
                "color": background,
                "connects_to": set([make_label(subdep) for subdep in self.__deps.values()])
            }
        }
        for dep in self.get_dep():
            nodes[make_label(dep)] = {
                "text": dep.name,
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

    def __get_all_deps(self, seen: Set[str]) -> List[NamedSchema]:
        '''
        Recursively traverses the dependency tree to generate a flat list.

        This method avoids cycles and duplicate entries by keeping track of
        visited nodes in the 'seen' set.

        Args:
            seen (set): A set of dependency names that have already been visited.

        Returns:
            list: A flat list of all dependency objects.
        '''
        deps = []

        for obj in self.__deps.values():
            if obj.name in seen:
                continue

            deps.append(obj)
            seen.add(obj.name)

            if not isinstance(obj, DependencySchema):
                # nothing to iterate over
                continue

            for obj_dep in obj.__get_all_deps(seen):
                deps.append(obj_dep)
                seen.add(obj_dep.name)

        return deps

    def get_dep(self, name: Optional[str] = None, hierarchy: bool = True) -> List[NamedSchema]:
        '''
        Returns all dependencies associated with this object or a specific one if requested.

        Raises:
            KeyError: if the specific module is requested but not found.

        Args:
            name (str): Name of the module.
            hierarchy (bool): If True, will return all modules including children,
                otherwise only this object's modules are returned.

        Returns:
            list: A list of dependency objects.
        '''

        if name:
            if not self.has_dep(name):
                if "." in name:
                    name0, *name1 = name.split(".")
                    subdep = self.get_dep(name0)
                    if isinstance(subdep, DependencySchema):
                        return subdep.get_dep(".".join(name1))
                    raise KeyError(f"{name} does not contain dependency information")
                raise KeyError(f"{name} is not an imported module")

            return self.__deps[name]

        if hierarchy:
            return self.__get_all_deps(set())
        return list(self.__deps.values())

    def has_dep(self, name: Union[NamedSchema, str]) -> bool:
        '''
        Checks if a specific dependency is present.

        Args:
            name (str): Name of the module.

        Returns:
            True if the module was found, False otherwise.
        '''

        if isinstance(name, NamedSchema):
            name = name.name

        return name in self.__deps

    def remove_dep(self, name: Union[str, NamedSchema]) -> bool:
        '''
        Removes a previously registered module.

        Args:
            name (str): Name of the module.

        Returns:
            True if the module was removed, False if it was not found.
        '''
        if not self.has_dep(name):
            return False

        if isinstance(name, NamedSchema):
            name = name.name

        del self.__deps[name]

        # Remove from dependency list
        dependencies = self.get("deps")
        dependencies.remove(name)

        self.set("deps", False, field="lock")
        self.set("deps", dependencies)
        self.set("deps", True, field="lock")

        return True

    def _populate_deps(self, module_map: Dict[str, NamedSchema]) -> None:
        '''
        Internal method to populate the internal dependency dictionary.

        This is used to reconstruct object references from a serialized format
        by looking up dependency names in the provided map.

        Args:
            module_map (dict): A dictionary mapping module names to module objects.
        '''
        if self.__deps:
            return

        for module in self.get("deps"):
            if module not in module_map:
                raise ValueError(f"{module} not available in map")
            self.__deps[module] = module_map[module]

            if isinstance(self.__deps[module], DependencySchema):
                self.__deps[module]._populate_deps(module_map)

    def _reset_deps(self) -> None:
        '''Resets the internal dependency dictionary.'''
        self.__deps = {}

    def check_filepaths(self, ignore_keys: Optional[List[Tuple[str, ...]]] = None) -> bool:
        '''
        Verifies that paths to all files in manifest are valid.

        Args:
            ignore_keys (list of keypaths): list of keypaths to ignore while checking

        Returns:
            True if all file paths are valid, otherwise False.
        '''
        error = False
        for obj in [self, *self.get_dep()]:
            if not isinstance(obj, PathSchemaBase):
                continue
            error |= not PathSchemaBase.check_filepaths(obj, ignore_keys=ignore_keys)
        return not error
