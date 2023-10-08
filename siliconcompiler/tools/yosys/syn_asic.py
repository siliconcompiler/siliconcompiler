
from siliconcompiler.tools.yosys.yosys import syn_setup, syn_post_process
import os
import re
import siliconcompiler.tools.yosys.prepareLib as prepareLib
import siliconcompiler.tools.yosys.mergeLib as mergeLib


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
    task = chip._get_task(step, index)

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

    for var0, var1 in [('yosys_tiehigh_cell', 'yosys_tiehigh_port'),
                       ('yosys_tiehigh_cell', 'yosys_tiehigh_port')]:
        key0 = ['library', mainlib, 'option', 'var', var0]
        key1 = ['library', mainlib, 'option', 'var', var1]
        if chip.valid(*key0):
            chip.add('tool', tool, 'task', task, 'require', ",".join(key1), step=step, index=index)
        if chip.valid(*key1):
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

    # document parameters
    chip.set('tool', tool, 'task', task, 'var', 'preserve_modules',
             'List of modules in input files to prevent flatten from "flattening"', field='help')
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
    chip.set('tool', tool, 'task', task, 'var', 'abc_constraint_load',
             'Capacitive load for the abc techmapping in fF, if not specified it will not be used',
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


################################
# mark cells dont use and format liberty files for yosys and abc
################################
def prepare_synthesis_libraries(chip):
    tool = 'yosys'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)
    corners = chip.get('tool', tool, 'task', task, 'var', 'synthesis_corner',
                       step=step, index=index)

    # mark dff libery file with dont use
    dff_liberty_file = chip.find_files('tool', tool, 'task', task, 'file', 'dff_liberty',
                                       step=step, index=index)[0]
    dff_dont_use = []
    for lib in chip.get('asic', 'logiclib', step=step, index=index):
        dontuse = chip.get('library', lib, 'asic', 'cells', 'dontuse', step=step, index=index)
        if dff_liberty_file in chip.find_files(*_get_synthesis_library_key(chip, lib, corners),
                                               step=step, index=index):
            # if we have the exact library, use those dontuses,
            # otherwise continue to build full list
            dff_dont_use = dontuse
            break

        dff_dont_use.extend(dontuse)

    with open(chip.get('tool', tool, 'task', task, 'file', 'dff_liberty_file',
                       step=step, index=index)[0], 'w') as f:
        f.write(prepareLib.processLibertyFile(
            dff_liberty_file,
            dont_use=dff_dont_use,
            logger=None if chip.get('option', 'quiet', step=step, index=index) else chip.logger
        ))

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
            lib_content = []
            # Mark dont use
            for lib_file in get_synthesis_libraries(lib):
                lib_content.append(
                    prepareLib.processLibertyFile(
                        lib_file,
                        logger=None if chip.get('option', 'quiet',
                                                step=step, index=index) else chip.logger
                    ))

            if not lib_content:
                continue

            var_name = 'synthesis_libraries'
            if libtype == "macrolib":
                var_name = 'synthesis_libraries_macros'

            lib_content = mergeLib.mergeLib(f"{lib}_merged", lib_content[0], lib_content[1:])

            output_file = os.path.join(
                chip._getworkdir(step=step, index=index),
                'inputs',
                f'sc_{libtype}_{lib}.lib'
            )

            with open(output_file, 'w') as f:
                f.write(lib_content)

            chip.add('tool', tool, 'task', task, 'file', var_name, output_file,
                     step=step, index=index)


def create_abc_synthesis_constraints(chip):

    tool = 'yosys'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    abc_driver = chip.get('tool', tool, 'task', task, 'var', 'abc_constraint_driver',
                          step=step, index=index)
    if abc_driver:
        abc_driver = abc_driver[0]

    abc_load = chip.get('tool', tool, 'task', task, 'var', 'abc_constraint_load',
                        step=step, index=index)
    if abc_load:
        abc_load = float(abc_load[0])

    if not abc_driver and not abc_load:
        # neither is set so nothing to do
        return

    with open(chip.get('tool', tool, 'task', task, 'file', 'abc_constraint_file',
                       step=step, index=index)[0], "w") as f:
        if abc_driver:
            f.write(f"set_driving_cell {abc_driver}\n")
        if abc_load:
            # convert to fF
            if chip.get('unit', 'capacitance')[0] == 'p':
                abc_load *= 1000
            f.write(f"set_load {abc_load}\n")


def get_synthesis_corner(chip):
    tool = 'yosys'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

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
    task = chip._get_task(step, index)

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
    task = chip._get_task(step, index)

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
            with open(sdc, 'r') as f:
                lines = f.read().splitlines()

            # TODO: handle line continuations
            for line in lines:
                clock_period = re.findall(r"create_clock.*-period\s+([0-9\.]+)", line)
                if clock_period:
                    clock_period = float(clock_period[0]) * abc_clock_multiplier

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
    task = chip._get_task(step, index)

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
    tool, task = chip._get_tool_task(step, index)

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
             f"{chip._getworkdir(step=step, index=index)}/inputs/sc_dff_library.lib",
             step=step, index=index, clobber=True)
    chip.set('tool', tool, 'task', task, 'file', 'abc_constraint_file',
             f"{chip._getworkdir(step=step, index=index)}/inputs/sc_abc.constraints",
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
