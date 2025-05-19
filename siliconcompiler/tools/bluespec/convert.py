import os
import shutil
from siliconcompiler.tools._common import \
    add_require_input, add_frontend_requires, get_frontend_options, get_input_files, \
    get_tool_task, has_input_files
from siliconcompiler import utils
from siliconcompiler import sc_open

# Directory inside step/index dir to store bsc intermediate results.
VLOG_DIR = 'verilog'
BSC_DIR = 'bluespec'


def setup(chip):
    '''
    Performs high level synthesis to generate a verilog output
    '''

    if not has_input_files(chip, 'input', 'hll', 'bsv'):
        return "no files in [input,hll,bsv]"

    tool = 'bluespec'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)

    # Standard Setup
    refdir = 'tools/' + tool
    chip.set('tool', tool, 'exe', 'bsc')
    # This is technically the 'verbose' flag, but used alone it happens to give
    # us the version and exit cleanly, so we'll use it here.
    chip.set('tool', tool, 'vswitch', '-v')
    chip.set('tool', tool, 'version', '>=2021.07', clobber=False)

    chip.set('tool', tool, 'task', task, 'refdir', refdir,
             step=step, index=index,
             package='siliconcompiler', clobber=False)
    chip.set('tool', tool, 'task', task, 'threads', utils.get_cores(chip),
             step=step, index=index, clobber=False)

    # Input/Output requirements
    chip.add('tool', tool, 'task', task, 'output', chip.top() + '.v', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', chip.top() + '.dot', step=step, index=index)

    # Schema requirements
    add_require_input(chip, 'input', 'hll', 'bsv')
    add_frontend_requires(chip, ['idir', 'ydir', 'define'])


################################
# Pre-process
################################
def pre_process(chip):
    # bsc requires its output directory exists before being called.
    for path in (VLOG_DIR, BSC_DIR):
        if os.path.isdir(path):
            shutil.rmtree(path)
        os.makedirs(path)


################################
#  Custom runtime options
################################
def runtime_options(chip):
    cmdlist = []

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    opts = get_frontend_options(chip, ['idir', 'ydir', 'define'])

    cmdlist.append('-verilog')
    cmdlist.extend(['-vdir', VLOG_DIR])
    cmdlist.extend(['-bdir', BSC_DIR])
    cmdlist.extend(['-info-dir', 'reports'])
    cmdlist.append('-u')
    cmdlist.append('-v')

    cmdlist.append('-show-module-use')
    cmdlist.append('-sched-dot')

    cmdlist.extend(['-g', chip.top(step, index)])

    bsc_path = ':'.join(opts['ydir'] + ['%/Libraries'])
    cmdlist.extend(['-p', bsc_path])

    for value in opts['idir']:
        cmdlist.extend(['-I', value])
    for value in opts['define']:
        cmdlist.extend(['-D', value])

    sources = get_input_files(chip, 'input', 'hll', 'bsv', add_library_files=False)
    if len(sources) != 1:
        raise ValueError('Bluespec frontend only supports one source file!')
    cmdlist.extend(sources)

    return cmdlist


################################
# Post-process (post executable)
################################
def post_process(chip):
    ''' Tool specific function to run after step execution
    '''

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    shutil.copyfile(f"reports/{chip.top(step, index)}_combined_full.dot",
                    f"outputs/{chip.top()}.dot")

    extra_modules = set()
    use_file = os.path.join(VLOG_DIR, f"{chip.top(step, index)}.use")
    if os.path.exists(use_file):
        BSC_BASE = os.path.dirname(
            os.path.dirname(
                chip.get('record', 'toolpath', step=step, index=index)))
        BSC_LIB = os.path.join(BSC_BASE, "lib", "Verilog")

        with sc_open(use_file) as f:
            for module in f:
                module = module.strip()
                mod_path = os.path.join(BSC_LIB, f"{module}.v")
                if os.path.exists(mod_path):
                    extra_modules.add(mod_path)
                else:
                    chip.logger.warning(f"Unable to find module {module} source "
                                        f"files at: {BSC_LIB}")

    # bsc outputs each compiled module to its own Verilog file, so we
    # concatenate them all to create a pickled output we can pass along.
    design = chip.top()
    with open(os.path.join('outputs', f'{design}.v'), 'w') as pickled_vlog:
        for src in os.listdir(VLOG_DIR):
            if src.endswith(".v"):
                with sc_open(os.path.join(VLOG_DIR, src)) as vlog_mod:
                    pickled_vlog.write(vlog_mod.read())

        pickled_vlog.write("\n")
        pickled_vlog.write("// Bluespec imports\n\n")
        for vfile in extra_modules:
            with sc_open(os.path.join(BSC_LIB, vfile)) as vlog_mod:
                pickled_vlog.write(vlog_mod.read() + "\n")
