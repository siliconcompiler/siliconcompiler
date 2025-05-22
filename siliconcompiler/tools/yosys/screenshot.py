from siliconcompiler.tools.yosys import setup as tool_setup
import os
import siliconcompiler.tools.yosys.prepareLib as prepareLib
from siliconcompiler.tools._common.asic import get_libraries
from siliconcompiler.tools._common import get_tool_task


def make_docs(chip):
    from siliconcompiler.targets import asap7_demo
    chip.use(asap7_demo)


def setup(chip):
    '''
    Generate a screenshot of the design
    '''

    # Generic tool setup.
    tool_setup(chip)

    # ASIC-specific setup.
    # setup_asic(chip)

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)
    chip.set('tool', tool, 'task', task, 'input', [], step=step, index=index)
    chip.set('tool', tool, 'task', task, 'script', 'sc_screenshot.tcl',
             step=step, index=index)

    design = chip.top()
    chip.set('tool', tool, 'task', task, 'output', [design + '.dot', design + '.png'],
             step=step, index=index)


################################
# format liberty files for yosys
################################
def prepare_asic_libraries(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    # Clear in case of rerun
    for libtype in ('synthesis_libraries', 'synthesis_libraries_macros'):
        chip.set('tool', tool, 'task', task, 'file', libtype, [],
                 step=step, index=index)

    # Generate synthesis_libraries and synthesis_macro_libraries for Yosys use

    # mark libs with dont_use since ABC cannot get this information via its commands
    # this also ensures the liberty files have been decompressed and corrected formatting
    # issues that generally cannot be handled by yosys or yosys-abc
    def get_synthesis_libraries(lib):
        keypath = _get_synthesis_library_key(chip, lib)
        if keypath and chip.valid(*keypath):
            return chip.find_files(*keypath, step=step, index=index)
        return []

    for libtype in ('logic', 'macro'):
        for lib in get_libraries(chip, libtype):
            lib_content = {}
            # Mark dont use
            for lib_file in get_synthesis_libraries(lib):
                # Ensure a unique name is used for library
                lib_file_name_base = os.path.basename(lib_file)
                if lib_file_name_base.lower().endswith('.gz'):
                    lib_file_name_base = lib_file_name_base[0:-3]
                if lib_file_name_base.lower().endswith('.lib'):
                    lib_file_name_base = lib_file_name_base[0:-4]

                lib_file_name = lib_file_name_base
                unique_ident = 0
                while lib_file_name in lib_content:
                    lib_file_name = f'{lib_file_name_base}_{unique_ident}'
                    unique_ident += 1

                lib_content[lib_file_name] = prepareLib.process_liberty_file(
                        lib_file,
                        logger=None if chip.get('option', 'quiet',
                                                step=step, index=index) else chip.logger)

            if not lib_content:
                continue

            var_name = 'synthesis_libraries'
            if libtype == "macro":
                var_name = 'synthesis_libraries_macros'

            for file, content in lib_content.items():
                output_file = os.path.join(
                    chip.getworkdir(step=step, index=index),
                    'inputs',
                    f'sc_{libtype}_{lib}_{file}.lib'
                )

                with open(output_file, 'w') as f:
                    f.write(content)

                chip.add('tool', tool, 'task', task, 'file', var_name, output_file,
                         step=step, index=index)


def get_synthesis_corner(chip):
    tool = 'yosys'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)

    syn_corners = chip.get('tool', tool, 'task', task, 'var', 'synthesis_corner',
                           step=step, index=index)
    if syn_corners:
        return syn_corners

    # determine corner based on setup corner from constraints
    corner = None
    for constraint in chip.getkeys('constraint', 'timing'):
        checks = chip.get('constraint', 'timing', constraint, 'check', step=step, index=index)
        if "setup" in checks and not corner:
            corner = chip.get('constraint', 'timing', constraint, 'libcorner',
                              step=step, index=index)

    if not corner:
        # try getting it from first constraint with a valid libcorner
        for constraint in chip.getkeys('constraint', 'timing'):
            if not corner:
                corner = chip.get('constraint', 'timing', constraint, 'libcorner',
                                  step=step, index=index)

    return corner


def _get_synthesis_library_key(chip, lib):
    if chip.valid('library', lib, 'option', 'file', 'yosys_synthesis_libraries'):
        return ('library', lib, 'option', 'file', 'yosys_synthesis_libraries')

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    delaymodel = chip.get('asic', 'delaymodel', step=step, index=index)

    for corner in chip.getkeys('library', lib, 'output'):
        if chip.valid('library', lib, 'output', corner, delaymodel):
            return ('library', lib, 'output', corner, delaymodel)

    return None


##################################################
def pre_process(chip):
    ''' Tool specific function to run before step execution
    '''

    prepare_asic_libraries(chip)
