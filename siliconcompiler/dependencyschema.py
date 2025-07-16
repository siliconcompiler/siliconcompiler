import os.path

from siliconcompiler.schema.baseschema import BaseSchema
from siliconcompiler.schema.editableschema import EditableSchema
from siliconcompiler.schema.parameter import Parameter, Scope
from siliconcompiler.schema.namedschema import NamedSchema


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
                shorthelp="List of object dependencies",
                help="List of named object dependencies included via add_dep()."))

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
