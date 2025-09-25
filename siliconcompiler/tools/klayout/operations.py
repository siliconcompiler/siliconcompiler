from siliconcompiler.tools.klayout import KLayoutTask


class OperationsTask(KLayoutTask):
    def __init__(self):
        super().__init__()

        self.add_parameter(
            "operations",
            "[(<merge,add,rotate,outline,rename,swap,add_top,write,convert_property,"
            "flatten,merge_shapes,delete_layers,rename_cell>,str)]",
            "list of operations to perform")
        self.add_parameter("stream", "<gds,oas>",
                           "Extension to use for stream generation", defvalue="gds")
        self.add_parameter("timestamps", "bool",
                           "Export GDSII with timestamps", defvalue=True)

    def task(self):
        return "operations"

    def setup(self):
        '''
        Perform unit operations on stream files. Currently supports:

            * rotating (rotate)
            * renaming (rename)
            * merging streams (merge)
            * adding streams together (add)
            * adding outline to top (outline)
            * swapping cells (swap)
            * adding new top cell (add_top)
            * renaming cells (rename_cell)
            * flatten
            * deleting layers
            * merging shapes
            * writing (write)
            * converting properties into text labels on design (convert_property)

        To rotate:

        >>> project.add('tool', 'klayout', 'task', 'operations', 'var', 'operations', 'rotate')

        To rename:

        >>> project.add('tool', 'klayout', 'task', 'operations', 'var', 'operations', \\
            'rename:tool,klayout,task,operations,var,new_name')
        >>> project.set('tool', 'klayout', 'task', 'operations', 'var', 'new_name', \\
            'chip_top')

        To merge streams:

        >>> project.add('tool', 'klayout', 'task', 'operations', 'var', 'operations', \\
            'merge:tool,klayout,task,operations,file,fill_stream')
        >>> project.set('tool', 'klayout', 'task', 'operations', 'file', 'fill_stream', \\
            './fill.gds')

        or to get it from the inputs to this task:

        >>> project.add('tool', 'klayout', 'task', 'operations', 'var', 'operations', \\
            'merge:fill.gds')

        To add streams:

        >>> project.add('tool', 'klayout', 'task', 'operations', 'var', 'operations', \\
            'add:tool,klayout,task,operations,file,fill_stream')
        >>> project.set('tool', 'klayout', 'task', 'operations', 'file', 'fill_stream', \\
            './fill.gds')

        or to get it from the inputs to this task:

        >>> project.add('tool', 'klayout', 'task', 'operations', 'var', 'operations', \\
            'add:fill.gds')

        To add outline:

        >>> project.add('tool', 'klayout', 'task', 'operations', 'var', 'operations', \\
            'outline:tool,klayout,task,operations,var,outline')
        >>> project.set('tool', 'klayout', 'task', 'operations', 'var', 'outline', \\
            ['10', '1'])  # layer / purpose pair

        To swap layout cells:

        >>> project.add('tool', 'klayout', 'task', 'operations', 'var', 'operations', \\
            'swap:tool,klayout,task,operations,var,cell_swap')
        >>> project.set('tool', 'klayout', 'task', 'operations', 'var', 'cell_swap', \\
            ['dummy_ANDX2=ANDX2', 'dummy_NANDX2=NANDX2'])

        To rename cells:

        >>> project.add('tool', 'klayout', 'task', 'operations', 'var', 'operations', \\
            'rename_cell:tool,klayout,task,operations,var,rename_cell')
        >>> project.set('tool', 'klayout', 'task', 'operations', 'var', 'rename_cell', \\
            ['dummy_ANDX2=ANDX2', 'dummy_NANDX2=NANDX2'])

        To add new top cell:

        >>> project.add('tool', 'klayout', 'task', 'operations', 'var', 'operations', \\
            'add_top:tool,klayout,task,operations,var,new_name')
        >>> project.set('tool', 'klayout', 'task', 'operations', 'var', 'new_name', \\
            'chip_top')

        To write out a new file:

        >>> project.add('tool', 'klayout', 'task', 'operations', 'var', 'operations', \\
            'write:combined.gds')

        To convert stream properties to text labels:

        >>> project.add('tool', 'klayout', 'task', 'operations', 'var', 'operations', \\
            'convert_property:tool,klayout,task,operations,var,convert_c4_bumps')
        >>> project.set('tool', 'klayout', 'task', 'operations', 'var', 'convert_c4_bumps', \\
            ['10', '2', \\  # layer / purpose pair for the source of the labels
            '3' \\  # stream property number
            '85', '5'])  #  (optional) destination layer / purpose pair, if not provided
                        # the source pair will be used instead.
        '''
        super().setup()

        self.set_script("klayout_operations.py")

        default_stream = self.get("var", "stream")

        self.add_input_file(ext=default_stream)
        self.add_output_file(ext=default_stream)

        self.add_required_key("var", "operations")
        self.add_required_key("var", "stream")
        self.add_required_key("var", "timestamps")

        for klayout_op, args in self.get("var", "operations"):
            if args is None:
                args = ""

            if klayout_op in ('add', 'merge'):
                if ',' in args:
                    self.add_required_key(*args.split(","))
                elif args:
                    self.add_input_file(args)
                else:
                    raise ValueError(f'{klayout_op} requires a filename to read or a keypath')
            elif klayout_op in ('outline',
                                'rename',
                                'swap',
                                'add_top',
                                'convert_property',
                                'merge_shapes',
                                'delete_layers',
                                'rename_cell'):
                self.add_required_key(*args.split(","))
            elif klayout_op in ('rotate', 'flatten'):
                if args:
                    raise ValueError('rotate/flatten do not take any arguments')
            elif klayout_op == 'write':
                if not args:
                    raise ValueError('write requires a filename to save to')
                self.add_output_file(args)

    def add_operation(self, op, args, step=None, index=None):
        self.add("var", "operations", (op, args), step=step, index=index)
        if args is None:
            args = ""
        if op in (
                'outline',
                'rename',
                'swap',
                'add_top',
                'convert_property',
                'merge_shapes',
                'delete_layers',
                'rename_cell') or (op in ('add', 'merge') and "," in args):
            keypath = args.split(",")
            if not self.valid(*keypath):
                self.add_parameter(keypath[-1], "[str]", "klayout operations arg")
