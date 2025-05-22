from siliconcompiler import utils
from siliconcompiler.tools import slang
import os
from siliconcompiler.tools._common import get_tool_task, has_input_files
from siliconcompiler.tools.slang import pyslang


def setup(chip):
    '''
    Elaborate verilog design files and generate a unified file.
    '''
    if slang.test_version():
        return slang.test_version()

    if not has_input_files(chip, 'input', 'rtl', 'verilog') and \
       not has_input_files(chip, 'input', 'rtl', 'systemverilog'):
        return "no files in [input,rtl,systemverilog] or [input,rtl,verilog]"

    slang.setup(chip)

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'task', task, 'threads', utils.get_cores(chip),
             clobber=False, step=step, index=index)

    chip.set('tool', tool, 'task', task, 'stdout', 'destination', 'log', step=step, index=index)
    chip.set('tool', tool, 'task', task, 'stderr', 'destination', 'log', step=step, index=index)

    chip.set('tool', tool, 'task', task, 'output', __outputfile(chip), step=step, index=index)

    chip.set('tool', tool, 'task', task, 'var', 'include_source_paths', True,
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'var', 'include_source_paths',
             "true/false, if true add the source file path information", field="help")


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

    def proc_range(range):
        files.add(manager.getFileName(range.start))
        files.add(manager.getFileName(range.end))

    while not nodes.empty():
        node = nodes.get()
        proc_range(node.sourceRange)
        for token in node:
            if isinstance(token, pyslang.Token):
                proc_range(token.range)
            else:
                nodes.put(token)

    return sorted([os.path.abspath(f) for f in files if os.path.isfile(f)])


def run(chip):
    # Override default errors
    ignored = [
        pyslang.Diags.MissingTimeScale,
        pyslang.Diags.UsedBeforeDeclared,
        pyslang.Diags.UnusedParameter,
        pyslang.Diags.UnusedDefinition,
        pyslang.Diags.UnusedVariable,
        pyslang.Diags.UnusedPort,
        pyslang.Diags.UnusedButSetNet,
        pyslang.Diags.UnusedImplicitNet,
        pyslang.Diags.UnusedButSetVariable,
        pyslang.Diags.UnusedButSetPort,
        pyslang.Diags.UnusedTypedef,
        pyslang.Diags.UnusedGenvar,
        pyslang.Diags.UnusedAssertionDecl
    ]

    driver, exitcode = slang._get_driver(
        chip,
        runtime_options,
        ignored_diagnotics=ignored)
    if exitcode:
        return exitcode

    compilation, ok = slang._compile(chip, driver)

    slang._diagnostics(chip, driver, compilation)

    manager = compilation.sourceManager

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)
    add_source = chip.get('tool', tool, 'task', task, 'var', 'include_source_paths',
                          step=step, index=index)[0] == 'true'

    def print_files(out, files):
        for src_file in files:
            out.write(f'//   File: {src_file}\n')

    with open(f'outputs/{__outputfile(chip)}', 'w') as out:
        for tree in compilation.getSyntaxTrees():
            files = []
            if add_source:
                files = __get_files(manager, tree)

            writer = pyslang.SyntaxPrinter(manager)

            writer.setIncludeMissing(False)
            writer.setIncludeSkipped(False)
            writer.setIncludeDirectives(False)

            writer.setIncludePreprocessed(True)
            writer.setIncludeTrivia(True)
            writer.setIncludeComments(True)
            writer.setSquashNewlines(True)

            out.write("////////////////////////////////////////////////////////////////\n")
            out.write("// Start:\n")
            print_files(out, files)

            out.write(writer.print(tree).str() + '\n')

            out.write("// End:\n")
            print_files(out, files)
            out.write("////////////////////////////////////////////////////////////////\n")

    if ok:
        return 0
    else:
        return 1


def runtime_options(chip):
    options = slang.common_runtime_options(chip)
    options.extend([
        "--allow-use-before-declare",
        "--ignore-unknown-modules",
        "-Weverything"
    ])

    return options
