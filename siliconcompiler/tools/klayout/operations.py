import os
from siliconcompiler import SiliconCompilerError
from siliconcompiler.tools.klayout.klayout import setup as setup_tool
from siliconcompiler.tools.klayout.klayout import process_metrics
from siliconcompiler.tools.klayout.klayout import runtime_options as runtime_options_tool
from siliconcompiler.tools._common import input_provides, get_tool_task


def setup(chip):
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

    >>> chip.add('tool', 'klayout, 'task', 'operations', 'var', 'operations', 'rotate')

    To rename:

    >>> chip.add('tool', 'klayout, 'task', 'operations', 'var', 'operations', \\
        'rename:tool,klayout,task,operations,var,new_name')
    >>> chip.set('tool', 'klayout, 'task', 'operations', 'var', 'new_name', \\
        'chip_top')

    To merge streams:

    >>> chip.add('tool', 'klayout, 'task', 'operations', 'var', 'operations', \\
        'merge:tool,klayout,task,operations,file,fill_stream')
    >>> chip.set('tool', 'klayout, 'task', 'operations', 'file', 'fill_stream', \\
        './fill.gds')

    or to get it from the inputs to this task:

    >>> chip.add('tool', 'klayout, 'task', 'operations', 'var', 'operations', \\
        'merge:fill.gds')

    To add streams:

    >>> chip.add('tool', 'klayout, 'task', 'operations', 'var', 'operations', \\
        'add:tool,klayout,task,operations,file,fill_stream')
    >>> chip.set('tool', 'klayout, 'task', 'operations', 'file', 'fill_stream', \\
        './fill.gds')

    or to get it from the inputs to this task:

    >>> chip.add('tool', 'klayout, 'task', 'operations', 'var', 'operations', \\
        'add:fill.gds')

    To add outline:

    >>> chip.add('tool', 'klayout, 'task', 'operations', 'var', 'operations', \\
        'outline:tool,klayout,task,operations,var,outline')
    >>> chip.set('tool', 'klayout, 'task', 'operations', 'var', 'outline', \\
        ['10', '1'])  # layer / purpose pair

    To swap layout cells:

    >>> chip.add('tool', 'klayout, 'task', 'operations', 'var', 'operations', \\
        'swap:tool,klayout,task,operations,var,cell_swap')
    >>> chip.set('tool', 'klayout, 'task', 'operations', 'var', 'cell_swap', \\
        ['dummy_ANDX2=ANDX2', 'dummy_NANDX2=NANDX2'])

    To rename cells:

    >>> chip.add('tool', 'klayout, 'task', 'operations', 'var', 'operations', \\
        'rename_cell:tool,klayout,task,operations,var,rename_cell')
    >>> chip.set('tool', 'klayout, 'task', 'operations', 'var', 'rename_cell', \\
        ['dummy_ANDX2=ANDX2', 'dummy_NANDX2=NANDX2'])

    To add new top cell:

    >>> chip.add('tool', 'klayout, 'task', 'operations', 'var', 'operations', \\
        'add_top:tool,klayout,task,operations,var,new_name')
    >>> chip.set('tool', 'klayout, 'task', 'operations', 'var', 'new_name', \\
        'chip_top')

    To write out a new file:

    >>> chip.add('tool', 'klayout, 'task', 'operations', 'var', 'operations', \\
        'write:combined.gds')

    To convert stream properties to text labels:

    >>> chip.add('tool', 'klayout, 'task', 'operations', 'var', 'operations', \\
        'convert_property:tool,klayout,task,operations,var,convert_c4_bumps')
    >>> chip.set('tool', 'klayout, 'task', 'operations', 'var', 'convert_c4_bumps', \\
        ['10', '2', \\  # layer / purpose pair for the source of the labels
         '3' \\  # stream property number
         '85', '5'])  #  (optional) destination layer / purpose pair, if not provided
                      # the source pair will be used instead.
    '''

    # Generic tool setup.
    setup_tool(chip)

    tool = 'klayout'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)
    clobber = False

    chip.set('tool', tool, 'task', task, 'threads', 1, step=step, index=index, clobber=clobber)

    script = 'klayout_operations.py'
    option = ['-z', '-nc', '-rx', '-r']
    chip.set('tool', tool, 'task', task, 'script', script, step=step, index=index, clobber=clobber)
    chip.set('tool', tool, 'task', task, 'option', option, step=step, index=index, clobber=clobber)

    # Set stream extension
    streams = ('gds', 'oas')
    chip.set('tool', tool, 'task', task, 'var', 'stream', 'gds',
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'var', 'stream',
             f'Extension to use for stream generation ({streams})',
             field='help')
    default_stream = chip.get('tool', tool, 'task', task, 'var', 'stream',
                              step=step, index=index)[0]
    # Input/Output requirements for default flow
    design = chip.top()
    if f'{design}.{default_stream}' in input_provides(chip, step, index):
        chip.add('tool', tool, 'task', task, 'input', f'{design}.{default_stream}',
                 step=step, index=index)
    else:
        chip.add('tool', tool, 'task', task, 'require', f'input,layout,{default_stream}')
    chip.add('tool', tool, 'task', task, 'output', f'{design}.{default_stream}',
             step=step, index=index)

    # Export GDS with timestamps by default.
    chip.set('tool', tool, 'task', task, 'var', 'timestamps', 'true',
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'var', 'timestamps',
             'Export GDSII with timestamps',
             field='help')

    klayout_ops = ('merge',
                   'add',
                   'rotate',
                   'outline',
                   'rename',
                   'swap',
                   'add_top',
                   'write',
                   'convert_property',
                   'flatten',
                   'merge_shapes',
                   'delete_layers',
                   'rename_cell')
    ops = chip.get('tool', tool, 'task', task, 'var', 'operations', step=step, index=index)
    for op in ops:
        klayout_op = op.split(':', 1)
        if len(klayout_op) == 1:
            klayout_op = klayout_op[0]
            args = ""
        else:
            klayout_op, args = klayout_op

        if klayout_op not in klayout_ops:
            raise SiliconCompilerError(
                f'{klayout_op} is not a supported operation in klayout: {klayout_ops}',
                chip=chip)

        if klayout_op in ('add', 'merge'):
            if ',' in args:
                chip.add('tool', tool, 'task', task, 'require', args, step=step, index=index)
            elif args:
                chip.add('tool', tool, 'task', task, 'input', args, step=step, index=index)
            else:
                raise SiliconCompilerError(
                    f'{klayout_op} requires a filename to read or a keypath', chip=chip)
        elif klayout_op in ('outline',
                            'rename',
                            'swap',
                            'add_top',
                            'convert_property',
                            'merge_shapes',
                            'delete_layers',
                            'rename_cell'):
            chip.add('tool', tool, 'task', task, 'require', args, step=step, index=index)
        elif klayout_op in ('rotate', 'flatten'):
            if args:
                raise SiliconCompilerError('rotate does not take any arguments', chip=chip)
        elif klayout_op in ('write'):
            if not args:
                raise SiliconCompilerError('write requires a filename to save to', chip=chip)
            chip.add('tool', tool, 'task', task, 'output', args,
                     step=step, index=index)


def runtime_options(chip):
    return runtime_options_tool(chip) + [
        '-rd', f'SC_TOOLS_ROOT={os.path.dirname(os.path.dirname(__file__))}'
    ]


def post_process(chip):
    process_metrics(chip)
