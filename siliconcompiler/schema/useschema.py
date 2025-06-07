import os.path

from .namedschema import NamedSchema


class UseSchema:
    '''
    Schema extension to add :meth:`.use` capability to a schema section.
    '''

    def __init__(self):
        self.__used = {}

    def use(self, obj: NamedSchema, clobber: bool = True) -> bool:
        """
        Adds a module to this object.

        Returns:
            True if object was imported, otherwise false.

        Args:
            obj (:class:`NamedSchema`): Module to add
        """

        if not isinstance(obj, NamedSchema):
            raise TypeError(f"Cannot use an object of type: {type(obj)}")

        if not clobber and obj.name() in self.__used:
            return False

        self.__used[obj.name()] = obj
        obj._reset()

        return True

    def write_usegraph(self, filename: str,
                       fontcolor: str = '#000000',
                       background: str = 'transparent',
                       fontsize: str = '14',
                       border: bool = True, landscape: bool = False) -> None:
        r'''
        Renders and saves the use graph to a file.

        Args:
            filename (filepath): Output filepath
            fontcolor (str): Node font RGB color hex value
            background (str): Background color
            fontsize (str): Node text font size
            border (bool): Enables node border if True
            landscape (bool): Renders graph in landscape layout if True

        Examples:
            >>> use.write_usegraph('mydump.png')
            Renders the object use graph and writes the result to a png file.
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
                "connects_to": set([make_label(subdep) for subdep in self.__used.values()])
            }
        }
        for dep in self.get_all_used():
            nodes[make_label(dep)] = {
                "text": dep.name(),
                "shape": "oval",
                "color": background,
                "connects_to": set([make_label(subdep) for subdep in dep.__used.values()])
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

    def get_use(self, name: str) -> NamedSchema:
        '''
        Returns a used module which has been imported.

        Raises:
            KeyError: if the module is not found

        Args:
            name (str): name of the module
        '''

        if name not in self.__used:
            raise KeyError(f"{name} is not an imported module")

        return self.__used[name]

    def __get_all_used(self, seen: set) -> list:
        '''
        Loop through the use tree and generate a flat list
        '''
        deps = []

        for obj in self.__used.values():
            if obj.name() in seen:
                continue

            deps.append(obj)
            seen.add(obj.name())

            if not isinstance(obj, UseSchema):
                # nothing to iterate over
                continue

            for obj_dep in obj.__get_all_used(seen):
                deps.append(obj_dep)
                seen.add(obj_dep.name())

        return deps

    def get_all_used(self, hierarchy: bool = True) -> list:
        '''
        Returns all used modules associated with this object.

        Args:
            hierarchy (bool): if True, will return all modules including children
                otherwise only this objects modules are returned.
        '''

        if hierarchy:
            return self.__get_all_used(set())
        return list(self.__used.values())

    def remove_use(self, name: str) -> bool:
        '''
        Removes a previously registered module.

        Args:
            name (str): name of the module

        Returns:
            True if the module was removed, False is not found.
        '''
        if name not in self.__used:
            return False

        del self.__used[name]
        return True
