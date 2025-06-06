import os.path

from .namedschema import NamedSchema


class UseSchema:
    '''
    Schema extension to add :meth:`.use` capability to a schema section.
    '''

    def __init__(self):
        self.__imported = {}

    def use(self, obj: NamedSchema, clobber: bool = True) -> bool:
        """
        Adds a module as a dependency.

        Returns:
            True if object was imported, otherwise false.

        Args:
            obj (:class:`NamedSchema`): Dependency to add
        """

        if not isinstance(obj, NamedSchema):
            raise TypeError(f"Cannot use an object of type: {type(obj)}")

        if not clobber and obj.name() in self.__imported:
            return False

        self.__imported[obj.name()] = obj
        obj._reset()

        return True

    def write_dependencygraph(self, filename: str,
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
            >>> use.write_dependencygraph('mydump.png')
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
                "connects_to": set([make_label(subdep) for subdep in self.__imported.values()])
            }
        }
        for dep in self.get_all_dependencies():
            nodes[make_label(dep)] = {
                "text": dep.name(),
                "shape": "oval",
                "color": background,
                "connects_to": set([make_label(subdep) for subdep in dep.__imported.values()])
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

    def get_dependency(self, name: str) -> NamedSchema:
        '''
        Returns a dependency which has been imported.

        Raises:
            KeyError: if the dependency is not found

        Args:
            name (str): name of the dependency
        '''

        if name not in self.__imported:
            raise KeyError(f"{name} is not an imported dependency")

        return self.__imported[name]

    def __get_all_dependencies(self, seen: set) -> list:
        '''
        Loop through the dependency tree and generate a flat list
        '''
        deps = []

        for obj in self.__imported.values():
            if obj.name() in seen:
                continue

            deps.append(obj)
            seen.add(obj.name())

            if not isinstance(obj, UseSchema):
                # nothing to iterate over
                continue

            for obj_dep in obj.__get_all_dependencies(seen):
                deps.append(obj_dep)
                seen.add(obj_dep.name())

        return deps

    def get_all_dependencies(self, hierarchy: bool = True) -> list:
        '''
        Returns all dependencies associated with this object.

        Args:
            hierarchy (bool): if True, will return all dependencies including children
                otherwise only this objects dependencies are returned.
        '''

        if hierarchy:
            return self.__get_all_dependencies(set())
        return list(self.__imported.values())

    def remove_dependency(self, name: str) -> bool:
        '''
        Removes a previously registered dependency.

        Args:
            name (str): name of the dependency

        Returns:
            True if the dependency was removed, False is not found.
        '''
        if name not in self.__imported:
            return False

        del self.__imported[name]
        return True
