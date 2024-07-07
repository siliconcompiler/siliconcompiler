
from siliconcompiler.tools.yosys.yosys import syn_setup, syn_post_process
import os
import re
import siliconcompiler.tools.yosys.prepareLib as prepareLib
from siliconcompiler import sc_open
from siliconcompiler import utils
from siliconcompiler.tools._common.asic import set_tool_task_var
from siliconcompiler.tools._common import get_tool_task


def make_docs(chip):
    chip.load_target("asap7_demo")


def setup(chip):
    '''
    Perform ASIC synthesis
    '''

    # Generic synthesis task setup.
    syn_setup(chip)

    # ASIC-specific setup.
    setup_asic(chip)


def setup_asic(chip):
    ''' Helper method for configs specific to ASIC steps (both syn and lec).
    '''

    tool = 'yosys'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)

    chip.add('tool', tool, 'task', task, 'require',
             ",".join(['asic', 'logiclib']),
             step=step, index=index)

    syn_corners = get_synthesis_corner(chip)

    if syn_corners is None:
        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['tool', tool, 'task', task, 'var', 'synthesis_corner']),
                 step=step, index=index)

    if syn_corners is not None:
        # add timing library requirements
        for lib in chip.get('asic', 'logiclib', step=step, index=index):
            # mandatory for logiclibs
            chip.add('tool', tool, 'task', task, 'require',
                     ",".join(_get_synthesis_library_key(chip, lib, syn_corners)),
                     step=step, index=index)

        for lib in chip.get('asic', 'macrolib', step=step, index=index):
            # optional for macrolibs
            if chip.valid(*_get_synthesis_library_key(chip, lib, syn_corners)):
                chip.add('tool', tool, 'task', task, 'require',
                         ",".join(_get_synthesis_library_key(chip, lib, syn_corners)),
                         step=step, index=index)
            elif chip.valid('library', lib, 'output', 'blackbox', 'verilog'):
                chip.add('tool', tool, 'task', task, 'require',
                         ",".join(['library', lib, 'output', 'blackbox', 'verilog']),
                         step=step, index=index)

    if chip.valid('input', 'constraint', 'sdc') and \
       chip.get('input', 'constraint', 'sdc', step=step, index=index):
        chip.add('tool', tool, 'task', task, 'require', 'input,constraint,sdc',
                 step=step, index=index)

    # set default control knobs
    logiclibs = chip.get('asic', 'logiclib', step=step, index=index)
    mainlib = logiclibs[0]
    for option, value in [
            ('flatten', "true"),
            ('hier_iterations', "10"),
            ('hier_threshold', "1000"),
            ('autoname', "true"),
            ('add_buffers', "true")]:
        chip.set('tool', tool, 'task', task, 'var', option, value,
                 step=step, index=index, clobber=False)
        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['tool', tool, 'task', task, 'var', option]),
                 step=step, index=index)

    # Add conditionally required mainlib variables
    if chip.valid('library', mainlib, 'option', 'var', 'yosys_buffer_cell'):
        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['library', mainlib, 'option', 'var', 'yosys_buffer_input']),
                 step=step, index=index)
        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['library', mainlib, 'option', 'var', 'yosys_buffer_output']),
                 step=step, index=index)

    library_has_addermap = \
        chip.valid('library', mainlib, 'option', 'file', 'yosys_addermap') and \
        chip.get('library', mainlib, 'option', 'file', 'yosys_addermap')
    chip.set('tool', tool, 'task', task, 'var', 'map_adders',
             "true" if library_has_addermap else "false",
             step=step, index=index, clobber=False)
    if chip.get('tool', tool, 'task', task, 'var', 'map_adders', step=step, index=index)[0] == \
       "true":
        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['tool', tool, 'task', task, 'var', 'map_adders']),
                 step=step, index=index)
        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['library', mainlib, 'option', 'file', 'yosys_addermap']),
                 step=step, index=index)

    for var0, var1 in [('memory_libmap', 'memory_techmap')]:
        key0 = ['tool', tool, 'tak', task, 'file', var0]
        key1 = ['tool', tool, 'tak', task, 'file', var1]
        if chip.valid(*key0) and chip.get(*key0, step=step, index=index):
            chip.add('tool', tool, 'task', task, 'require', ",".join(key1), step=step, index=index)
        if chip.valid(*key1) and chip.get(*key1, step=step, index=index):
            chip.add('tool', tool, 'task', task, 'require', ",".join(key0), step=step, index=index)

    chip.set('tool', tool, 'task', task, 'var', 'synthesis_corner', get_synthesis_corner(chip),
             step=step, index=index, clobber=False)
    chip.add('tool', tool, 'task', task, 'require',
             ",".join(['tool', tool, 'task', task, 'var', 'synthesis_corner']),
             step=step, index=index)

    # Require abc clock conversion factor, from library units to ps
    chip.add('tool', tool, 'task', task, 'require',
             ','.join(['library', mainlib, 'option', 'var', 'yosys_abc_clock_multiplier']),
             step=step, index=index)
    abc_driver = get_abc_driver(chip)
    if abc_driver:
        chip.set('tool', tool, 'task', task, 'var', 'abc_constraint_driver', abc_driver,
                 step=step, index=index, clobber=False)

    set_tool_task_var(chip, 'abc_constraint_load',
                      schelp='Capacitive load for the abc techmapping in fF, '
                             'if not specified it will not be used',
                      require='lib')

    # document parameters
    chip.set('tool', tool, 'task', task, 'var', 'preserve_modules',
             'List of modules in input files to prevent flatten from "flattening"', field='help')
    chip.set('tool', tool, 'task', task, 'var', 'blackbox_modules',
             'List of modules in input files to exclude from synthesis by replacing them '
             'with empty blackboxes"', field='help')
    chip.set('tool', tool, 'task', task, 'var', 'flatten',
             'true/false, invoke synth with the -flatten option', field='help')
    chip.set('tool', tool, 'task', task, 'var', 'autoname',
             'true/false, call autoname to rename wires based on registers', field='help')
    chip.set('tool', tool, 'task', task, 'var', 'map_adders',
             'true/false, techmap adders in Yosys', field='help')
    chip.set('tool', tool, 'task', task, 'var', 'synthesis_corner',
             'Timing corner to use for synthesis', field='help')
    chip.set('tool', tool, 'task', task, 'file', 'dff_liberty',
             'Liberty file to use for flip-flop mapping, if not specified the first in the '
             'logiclib is used', field='help')
    chip.set('tool', tool, 'task', task, 'var', 'abc_constraint_driver',
             'Buffer that drives the abc techmapping, defaults to first buffer specified',
             field='help')
    chip.set('tool', tool, 'task', task, 'file', 'abc_constraint_file',
             'File used to pass in constraints to abc', field='help')
    chip.set('tool', tool, 'task', task, 'var', 'abc_clock_period',
             'Clock period to use for synthesis in ps, if more than one clock is specified, the '
             'smallest period is used.', field='help')
    chip.set('tool', tool, 'task', task, 'var', 'abc_clock_derating',
             'Used to derate the clock period to further constrain the clock, '
             'values between 0 and 1', field='help')
    chip.set('tool', tool, 'task', task, 'file', 'techmap',
             'File to use for techmapping in Yosys', field='help')
    chip.set('tool', tool, 'task', task, 'file', 'dff_liberty_file',
             'File to use for the DFF mapping stage of Yosys', field='help')
    chip.set('tool', tool, 'task', task, 'var', 'add_buffers',
             'true/false, flag to indicate whether to add buffers or not.', field='help')

    chip.set('tool', tool, 'task', task, 'var', 'hier_iterations',
             'Number of iterations to attempt to determine the hierarchy to flatten',
             field='help')
    chip.set('tool', tool, 'task', task, 'var', 'hier_threshold',
             'Instance limit for the number of cells in a module to preserve.',
             field='help')

    chip.set('tool', tool, 'task', task, 'var', 'strategy',
             'ABC synthesis strategy. Allowed values are DELAY0-4, AREA0-3, or if the strategy '
             'starts with a + it is assumed to be actual commands for ABC.',
             field='help')

    chip.set('tool', tool, 'task', task, 'file', 'memory_libmap',
             'File used to map memories with yosys', field='help')
    chip.set('tool', tool, 'task', task, 'file', 'memory_techmap',
             'File used to techmap memories with yosys', field='help')

    chip.add('tool', tool, 'task', task, 'file', 'synth_extra_map',
             'tools/yosys/techmaps/lcu_kogge_stone.v', package='siliconcompiler',
             step=step, index=index)
    chip.set('tool', tool, 'task', task, 'file', 'synth_extra_map',
             'Files used in synthesis to perform additional techmapping', field='help')


################################
# mark cells dont use and format liberty files for yosys and abc
################################
def prepare_synthesis_libraries(chip):
    tool = 'yosys'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)
    corners = chip.get('tool', tool, 'task', task, 'var', 'synthesis_corner',
                       step=step, index=index)

    # mark dff libery file with dont use
    dff_liberty_file = chip.find_files('tool', tool, 'task', task, 'file', 'dff_liberty',
                                       step=step, index=index)[0]

    with open(chip.get('tool', tool, 'task', task, 'file', 'dff_liberty_file',
                       step=step, index=index)[0], 'w') as f:
        f.write(prepareLib.processLibertyFile(
            dff_liberty_file,
            logger=None if chip.get('option', 'quiet', step=step, index=index) else chip.logger
        ))

    # Clear in case of rerun
    for libtype in ('synthesis_libraries', 'synthesis_libraries_macros'):
        chip.set('tool', tool, 'task', task, 'file', libtype, [],
                 step=step, index=index)

    # Generate synthesis_libraries and synthesis_macro_libraries for Yosys use

    # mark libs with dont_use since ABC cannot get this information via its commands
    # this also ensures the liberty files have been decompressed and corrected formatting
    # issues that generally cannot be handled by yosys or yosys-abc
    def get_synthesis_libraries(lib):
        keypath = _get_synthesis_library_key(chip, lib, corners)
        if chip.valid(*keypath):
            return chip.find_files(*keypath, step=step, index=index)
        return []

    for libtype in ('logiclib', 'macrolib'):
        for lib in chip.get('asic', libtype, step=step, index=index):
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

                lib_content[lib_file_name] = prepareLib.processLibertyFile(
                        lib_file,
                        logger=None if chip.get('option', 'quiet',
                                                step=step, index=index) else chip.logger)

            if not lib_content:
                continue

            var_name = 'synthesis_libraries'
            if libtype == "macrolib":
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


def create_abc_synthesis_constraints(chip):

    tool = 'yosys'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)

    abc_driver = chip.get('tool', tool, 'task', task, 'var', 'abc_constraint_driver',
                          step=step, index=index)
    if abc_driver:
        abc_driver = abc_driver[0]

    abc_load = chip.get('tool', tool, 'task', task, 'var', 'abc_constraint_load',
                        step=step, index=index)
    if abc_load:
        abc_load = abc_load[0]

    if not abc_driver and not abc_load:
        # neither is set so nothing to do
        return

    with open(chip.get('tool', tool, 'task', task, 'file', 'abc_constraint_file',
                       step=step, index=index)[0], "w") as f:
        if abc_load:
            # convert to fF
            abc_load = re.match(r'([0-9]*\.?[0-9]*)\s*([fpa])[fF]?', abc_load)

            if not abc_load:
                raise ValueError(f'Unable to parse {abc_load}')

            abc_load_unit = abc_load.group(2)
            if not abc_load_unit:
                abc_load_unit = chip.get('unit', 'capacitance')[0]

            abc_load = float(abc_load.group(1))

            if abc_load_unit == 'p':
                abc_load *= 1000
            elif abc_load_unit == 'a':
                abc_load /= 1000

        abc_template = utils.get_file_template('abc.const',
                                               root=os.path.join(os.path.dirname(__file__),
                                                                 'templates'))
        f.write(abc_template.render(abc_driver=abc_driver, abc_load=abc_load))


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


def _get_synthesis_library_key(chip, lib, corners):
    if chip.valid('library', lib, 'option', 'file', 'yosys_synthesis_libraries'):
        return ('library', lib, 'option', 'file', 'yosys_synthesis_libraries')

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    delaymodel = chip.get('asic', 'delaymodel', step=step, index=index)
    for corner in corners:
        if chip.valid('library', lib, 'output', corner, delaymodel):
            return ('library', lib, 'output', corner, delaymodel)

    return ('library', lib, 'output', corners[0], delaymodel)


def get_dff_liberty_file(chip):
    tool = 'yosys'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)

    dff_liberty = None
    if chip.valid('tool', tool, 'task', task, 'file', 'dff_liberty'):
        dff_liberty = chip.find_files('tool', tool, 'task', task, 'file', 'dff_liberty',
                                      step=step, index=index)
        if dff_liberty:
            return dff_liberty[0]

    mainlib = chip.get('asic', 'logiclib', step=step, index=index)[0]
    if chip.valid('library', mainlib, 'option', 'file', 'yosys_dff_liberty'):
        dff_liberty = chip.find_files('library', mainlib, 'option', 'file', 'yosys_dff_liberty')
        if dff_liberty:
            return dff_liberty[0]

    corners = get_synthesis_corner(chip)
    if corners is None:
        return None

    # if dff liberty file is not set, use the first liberty file defined
    for lib in chip.get('asic', 'logiclib', step=step, index=index):
        if not chip.valid(*_get_synthesis_library_key(chip, lib, corners)):
            continue

        lib_files = chip.find_files(*_get_synthesis_library_key(chip, lib, corners),
                                    step=step, index=index)
        if len(lib_files) > 0:
            return lib_files[0]

    return None


def get_abc_period(chip):

    tool = 'yosys'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)

    logiclibs = chip.get('asic', 'logiclib', step=step, index=index)
    mainlib = logiclibs[0]

    abc_clock_period = chip.get('tool', tool, 'task', task, 'var', 'abc_clock_period',
                                step=step, index=index)
    if abc_clock_period:
        return abc_clock_period[0]

    period = None

    abc_clock_multiplier = float(chip.get('library', mainlib, 'option', 'var',
                                          'yosys_abc_clock_multiplier')[0])

    # get clock information from sdc files
    # TODO: fix for fpga/asic differentiation later
    if chip.valid('input', 'constraint', 'sdc'):
        for sdc in chip.find_files('input', 'constraint', 'sdc', step=step, index=index):
            lines = []
            with sc_open(sdc) as f:
                lines = f.read().splitlines()

            # collect simple variables in case clock is specified with a variable
            re_var = r"[A-Za-z0-9_]+"
            re_num = r"[0-9\.]+"
            sdc_vars = {}
            for line in lines:
                tcl_variable = re.findall(fr"^\s*set\s+({re_var})\s+({re_num})", line)
                if tcl_variable:
                    var_name, var_value = tcl_variable[0]
                    sdc_vars[f'${var_name}'] = float(var_value)

            # TODO: handle line continuations
            for line in lines:
                clock_period = re.findall(fr"create_clock\s.*-period\s+({re_num}|\${re_var})",
                                          line)
                if clock_period:
                    clock_period = clock_period[0]
                    if clock_period[0] == '$':
                        if clock_period in sdc_vars:
                            clock_period = sdc_vars[clock_period]
                        else:
                            chip.logger.warning('Unable to identify clock period from '
                                                f'{clock_period}.')
                            continue
                    else:
                        clock_period = float(clock_period)

                    clock_period = clock_period * abc_clock_multiplier

                    if period is None:
                        period = clock_period
                    else:
                        period = min(period, clock_period)

    if period is None:
        # get clock information from defined clocks
        for pin in chip.getkeys('datasheet', 'pin'):
            for mode in chip.getkeys('datasheet', 'pin', pin, 'type'):
                if chip.get('datasheet', 'pin', pin, 'type', mode) == 'clock':
                    clock_period = min(chip.get('datasheet', 'pin', pin, 'tperiod', mode)) * 1e12

                    if period is None:
                        period = clock_period
                    else:
                        period = min(period, clock_period)

    if period is None:
        return None

    abc_clock_derating = chip.get('tool', tool, 'task', task, 'var', 'abc_clock_derating',
                                  step=step, index=index)
    if abc_clock_derating:
        derating = float(abc_clock_derating[0])
        if derating > 1:
            chip.logger.warning("abc_clock_derating is greater than 1.0")
        elif derating > 0:
            period *= (1.0 - derating)
        else:
            chip.logger.error("abc_clock_derating is negative")

    return int(period)


def get_abc_driver(chip):

    tool = 'yosys'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)

    abc_driver = chip.get('tool', tool, 'task', task, 'var', 'abc_constraint_driver',
                          step=step, index=index)
    if abc_driver:
        return abc_driver[0]

    abc_driver = None
    # get the first driver defined in the logic lib
    for lib in chip.get('asic', 'logiclib', step=step, index=index):
        if chip.valid('library', lib, 'option', 'var', 'yosys_driver_cell') and not abc_driver:
            abc_driver = chip.get('library', lib, 'option', 'var', 'yosys_driver_cell')[0]

    return abc_driver


##################################################
def pre_process(chip):
    ''' Tool specific function to run before step execution
    '''

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    # copy techmapping from libraries
    logiclibs = chip.get('asic', 'logiclib', step=step, index=index)
    macrolibs = chip.get('asic', 'macrolib', step=step, index=index)
    for lib in logiclibs + macrolibs:
        if not chip.valid('library', lib, 'option', 'file', 'yosys_techmap'):
            continue
        for techmap in chip.find_files('library', lib, 'option', 'file', 'yosys_techmap'):
            if techmap is None:
                continue
            chip.add('tool', tool, 'task', task, 'file', 'techmap', techmap, step=step, index=index)

    # Constants needed by yosys, do not allow overriding of values so force clobbering
    chip.set('tool', tool, 'task', task, 'file', 'dff_liberty_file',
             f"{chip.getworkdir(step=step, index=index)}/inputs/sc_dff_library.lib",
             step=step, index=index, clobber=True)
    chip.set('tool', tool, 'task', task, 'file', 'abc_constraint_file',
             f"{chip.getworkdir(step=step, index=index)}/inputs/sc_abc.constraints",
             step=step, index=index, clobber=True)

    dff_liberty_file = get_dff_liberty_file(chip)
    if dff_liberty_file:
        chip.set('tool', tool, 'task', task, 'file', 'dff_liberty', dff_liberty_file,
                 step=step, index=index, clobber=False)

    abc_clock_period = get_abc_period(chip)
    if abc_clock_period:
        chip.set('tool', tool, 'task', task, 'var', 'abc_clock_period', str(abc_clock_period),
                 step=step, index=index, clobber=False)

    prepare_synthesis_libraries(chip)
    create_abc_synthesis_constraints(chip)
    return


def post_process(chip):
    syn_post_process(chip)
