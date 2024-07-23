import os
import shutil
import glob
from siliconcompiler.tools._common import add_frontend_requires, get_tool_task, has_input_files
from siliconcompiler import sc_open, SiliconCompilerError


def setup(chip):
    '''
    Performs high level synthesis to generate a verilog output
    '''

    if not has_input_files(chip, 'input', 'config', 'chisel') and \
       not has_input_files(chip, 'input', 'hll', 'scala'):
        return "no files in [input,hll,scala] or [input,config,chisel]"

    tool = 'chisel'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)

    # Standard Setup
    refdir = 'tools/' + tool
    chip.set('tool', tool, 'exe', 'sbt')
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=1.5.5', clobber=False)

    chip.set('tool', tool, 'task', task, 'refdir', refdir,
             step=step, index=index,
             package='siliconcompiler', clobber=False)
    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             step=step, index=index, clobber=False)

    chip.set('tool', tool, 'task', task, 'option', ['-batch',
                                                    '--no-share',
                                                    '--no-global'],
             step=step, index=index)

    chip.set('tool', tool, 'task', task, 'var', 'application',
             'Application name of the chisel program',
             field='help')
    chip.set('tool', tool, 'task', task, 'var', 'argument',
             'Arguments for the chisel build',
             field='help')

    # Input/Output requirements
    if chip.valid('input', 'config', 'chisel') and \
       chip.get('input', 'config', 'chisel', step=step, index=index):
        chip.add('tool', tool, 'task', task, 'require', 'input,config,chisel',
                 step=step, index=index)
        if len(chip.get('input', 'config', 'chisel', step=step, index=index)) != 1:
            raise SiliconCompilerError('Only one build.sbt is supported.', chip=chip)

    if chip.valid('input', 'hll', 'scala') and \
       chip.get('input', 'hll', 'scala', step=step, index=index):
        chip.add('tool', tool, 'task', task, 'require', 'input,hll,scala',
                 step=step, index=index)

    chip.add('tool', tool, 'task', task, 'output', chip.top() + '.v', step=step, index=index)

    add_frontend_requires(chip, [])


def pre_process(chip):
    tool = 'chisel'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)

    refdir = chip.find_files('tool', tool, 'task', task, 'refdir', step=step, index=index)[0]

    if chip.valid('input', 'config', 'chisel') and \
       chip.get('input', 'config', 'chisel', step=step, index=index):
        build_file = chip.find_files('input', 'config', 'chisel', step=step, index=index)[0]
        work_dir = chip.getworkdir(step=step, index=index)
        build_dir = os.path.dirname(build_file)
        # Expect file tree from: https://www.scala-sbt.org/1.x/docs/Directories.html
        # copy build.sbt
        # copy src/
        shutil.copyfile(build_file, os.path.join(work_dir, 'build.sbt'))
        shutil.copytree(os.path.join(build_dir, 'src'),
                        os.path.join(work_dir, 'src'))
        if os.path.exists(os.path.join(build_dir, 'project')):
            shutil.copytree(os.path.join(build_dir, 'project'),
                            os.path.join(work_dir, 'project'))
        return

    for filename in ('build.sbt', 'SCDriver.scala'):
        src = os.path.join(refdir, filename)
        dst = filename
        shutil.copyfile(src, dst)

    # Chisel driver relies on Scala files being collected into '$CWD/inputs'
    chip.set('input', 'hll', 'scala', True, field='copy')
    chip.collect(directory=os.path.join(chip.getworkdir(step=step, index=index), 'inputs'))


def runtime_options(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    design = chip.top()

    runMain = ["runMain"]
    if chip.valid('input', 'config', 'chisel') and \
       chip.get('input', 'config', 'chisel', step=step, index=index):
        app = design
        if chip.valid('tool', tool, 'task', task, 'var', 'application') and \
           chip.get('tool', tool, 'task', task, 'var', 'application', step=step, index=index):
            app = chip.get('tool', tool, 'task', task, 'var', 'application',
                           step=step, index=index)[0]

        runMain.append(f"{app}")

        if chip.valid('tool', tool, 'task', task, 'var', 'argument') and \
           chip.get('tool', tool, 'task', task, 'var', 'argument', step=step, index=index):
            runMain.extend(chip.get('tool', tool, 'task', task, 'var', 'argument',
                                    step=step, index=index))
        runMain.append("--")

        runMain.append("--target-dir chisel-output")
    else:
        # Use built in driver
        runMain.append("SCDriver")
        runMain.append(f"--module {chip.top(step=step, index=index)}")

        runMain.append(f"--output-file ../outputs/{design}.v")

    return [f'"{" ".join(runMain)}"']


def post_process(chip):
    chisel_path = 'chisel-output'
    if os.path.exists(chisel_path):
        design = chip.top()
        with open(f'outputs/{design}.v', 'w') as out:
            for f in glob.glob(os.path.join(chisel_path, '*.v')):
                with sc_open(f) as i_file:
                    out.writelines(i_file.readlines())
