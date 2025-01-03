'''
Lint system verilog
'''
from siliconcompiler.tools import slang
from siliconcompiler import sc_open
import os
import re
import pyslang
from siliconcompiler.tools._common import get_tool_task, record_metric, has_input_files


def setup(chip):
    '''
    Import verilog files
    '''

    if not has_input_files(chip, 'input', 'rtl', 'verilog') and \
       not has_input_files(chip, 'input', 'rtl', 'systemverilog'):
        return "no files in [input,rtl,systemverilog] or [input,rtl,verilog]"

    slang.setup(chip)

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             clobber=False, step=step, index=index)

    chip.set('tool', tool, 'task', task, 'stdout', 'destination', 'log', step=step, index=index)
    chip.set('tool', tool, 'task', task, 'stderr', 'destination', 'log', step=step, index=index)

    chip.set('tool', tool, 'task', task, 'output', __outputfile(chip), step=step, index=index)


def __outputfile(chip):
    is_systemverilog = has_input_files(chip, 'input', 'rtl', 'systemverilog')
    if is_systemverilog:
        return f'{chip.top()}.sv'
    return f'{chip.top()}.v'


def __get_files(manager, tree):
    files = set()

    from queue import Queue
    nodes = Queue(maxsize=0)
    nodes.put(tree.root)

    while (not nodes.empty()):
        node = nodes.get()
        files.add(manager.getFileName(node.sourceRange.start))
        files.add(manager.getFileName(node.sourceRange.end))
        for token in node:
            if isinstance(token, pyslang.Token):
                continue
            else:
                nodes.put(token)

    return [os.path.abspath(f) for f in files if os.path.isfile(f)]


def run(chip):
    driver, exitcode = slang._get_driver(chip, runtime_options)
    print(driver)
    if exitcode:
        return exitcode

    compilation, ok = slang._compile(chip, driver)
    print(compilation)

    manager = compilation.sourceManager

    print(dir(compilation))

    print(compilation.getRoot())

    with open(f'outputs/{__outputfile(chip)}', 'w') as out:
        for tree in compilation.getSyntaxTrees():
            files = __get_files(manager, tree)

            writer = pyslang.SyntaxPrinter(manager)
            writer.setIncludeTrivia(True)
            writer.setIncludeComments(True)
            writer.setSquashNewlines(True)
            for src_file in files:
                out.write(f'SC-Source: {src_file}\n')
            out.write(writer.print(tree).str() + '\n')

    if ok:
        return 0
    else:
        return 1


def runtime_options(chip):
    options = slang.runtime_options(chip)

    options.append("--ignore-unknown-modules")

    return options


def post_process(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    with sc_open(f'{step}.log') as f:
        for line in f:
            match = re.search(r'(\d+) errors, (\d+) warnings', line)
            if match:
                record_metric(chip, step, index, 'errors', match.group(1), f'{step}.log')
                record_metric(chip, step, index, 'warnings', match.group(2), f'{step}.log')
