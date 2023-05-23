
from siliconcompiler.tools.yosys.yosys import syn_setup, syn_post_process
import os
import re
import siliconcompiler.tools.yosys.markDontUse as markDontUse


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

    delaymodel = chip.get('asic', 'delaymodel', step=step, index=index)
    syn_corner = get_synthesis_corner(chip)

    if syn_corner is None:
        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['tool', tool, 'task', task, 'var', 'synthesis_corner']),
                 step=step, index=index)

    if syn_corner is not None:
        # add timing library requirements
        for lib in chip.get('asic', 'logiclib', step=step, index=index):
            # mandatory for logiclibs
            chip.add('tool', tool, 'task', task, 'require',
                     ",".join(['library', lib, 'output', syn_corner, delaymodel]),
                     step=step, index=index)

        for lib in chip.get('asic', 'macrolib', step=step, index=index):
            # optional for macrolibs
            if not chip.valid('library', lib, 'output', syn_corner, delaymodel):
                continue

            chip.add('tool', tool, 'task', task, 'require',
                     ",".join(['library', lib, 'output', syn_corner, delaymodel]),
                     step=step, index=index)

    # set default control knobs
    logiclibs = chip.get('asic', 'logiclib', step=step, index=index)
    mainlib = logiclibs[0]
    for option, value, additional_require in [
            ('flatten', "True", None),
            ('autoname', "True", None),
            ('add_buffers', "True", None),
            ('map_adders', "False", ['library', mainlib, 'option', 'file', 'yosys_addermap'])]:
        chip.set('tool', tool, 'task', task, 'var', option, value,
                 step=step, index=index, clobber=False)
        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['tool', tool, 'task', task, 'var', option]),
                 step=step, index=index)
        if additional_require is not None and chip.get('tool', tool, 'task', task, 'var', option,
                                                       step=step, index=index)[0] != "False":
            chip.add('tool', tool, 'task', task, 'require',
                     ",".join(additional_require),
                     step=step, index=index)

    # Add conditionally required mainlib variables
    if chip.valid('library', mainlib, 'option', 'var', 'yosys_buffer_cell'):
        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['library', mainlib, 'option', 'var', 'yosys_buffer_input']),
                 step=step, index=index)
        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['library', mainlib, 'option', 'var', 'yosys_buffer_output']),
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

    abc_driver = get_abc_driver(chip)
    if abc_driver:
        chip.set('tool', tool, 'task', task, 'var', 'abc_constraint_driver', abc_driver,
                 step=step, index=index, clobber=False)

    # document parameters
    chip.set('tool', tool, 'task', task, 'var', 'preserve_modules',
             'List of modules in input files to prevent flatten from "flattening"', field='help')
    chip.set('tool', tool, 'task', task, 'var', 'flatten',
             'True/False, invoke synth with the -flatten option', field='help')
    chip.set('tool', tool, 'task', task, 'var', 'autoname',
             'True/False, call autoname to rename wires based on registers', field='help')
    chip.set('tool', tool, 'task', task, 'var', 'map_adders',
             'False/path to map_adders, techmap adders in Yosys', field='help')
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
             'File used to pass in contraints to abc', field='help')
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
             'True/False, flag to indicate whether to add buffers or not.', field='help')


################################
# mark cells dont use and format liberty files for yosys and abc
################################
def prepare_synthesis_libraries(chip):

    tool = 'yosys'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)
    delaymodel = chip.get('asic', 'delaymodel', step=step, index=index)

    corner = chip.get('tool', tool, 'task', task, 'var', 'synthesis_corner',
                      step=step, index=index)[0]

    # mark dff libery file with dont use
    dff_liberty_file = chip.find_files('tool', tool, 'task', task, 'file', 'dff_liberty',
                                       step=step, index=index)[0]
    dff_dont_use = []
    for lib in chip.get('asic', 'logiclib', step=step, index=index):
        # Only process dontuse cells if they are defined in the Schema.
        if chip.valid('library', lib, 'asic', 'cells', 'dontuse'):
            dontuse = chip.get('library', lib, 'asic', 'cells', 'dontuse', step=step, index=index)
            if dff_liberty_file in chip.find_files('library', lib, 'output', corner, delaymodel,
                                                   step=step, index=index):
                # if we have the exact library, use those dontuses,
                # otherwise continue to build full list
                dff_dont_use = dontuse
                break

            dff_dont_use.extend(dontuse)

    markDontUse.processLibertyFile(
        dff_liberty_file,
        chip.get('tool', tool, 'task', task, 'file', 'dff_liberty_file',
                 step=step, index=index)[0],
        dff_dont_use,
        chip.get('option', 'quiet', step=step, index=index),
    )

    # Generate synthesis_libraries and synthesis_macro_libraries for Yosys use

    # mark libs with dont_use since ABC cannot get this information via its commands
    # this also ensures the liberty files have been decompressed and corrected formatting
    # issues that generally cannot be handled by yosys or yosys-abc
    def get_synthesis_libraries(lib):
        if chip.valid('library', lib, 'option', 'file', 'yosys_synthesis_libraries'):
            synthesis_libraries = chip.find_files('library', lib, 'option', 'file',
                                                  'yosys_synthesis_libraries')
        elif chip.valid('library', lib, 'output', corner, delaymodel):
            synthesis_libraries = chip.find_files('library', lib, 'output', corner, delaymodel,
                                                  step=step, index=index)
        else:
            synthesis_libraries = []

        return synthesis_libraries

    def process_lib_file(libtype, lib, lib_file, dont_use):
        input_base_name = os.path.splitext(os.path.basename(lib_file))[0]
        output_file = os.path.join(
            chip._getworkdir(step=step, index=index),
            'inputs',
            f'sc_{libtype}_{lib}_{input_base_name}.lib'
        )
        markDontUse.processLibertyFile(lib_file, output_file, dont_use,
                                       chip.get('option', 'quiet', step=step, index=index))

        var_name = 'synthesis_libraries'
        if (libtype == "macrolib"):
            var_name = 'synthesis_libraries_macros'

        chip.add('tool', tool, 'task', task, 'file', var_name, output_file, step=step, index=index)

    for libtype in ('logiclib', 'macrolib'):
        for lib in chip.get('asic', libtype, step=step, index=index):
            # Only process dontuse cells if they are defined in the Schema.
            dont_use = []
            if chip.valid('library', lib, 'asic', 'cells', 'dontuse'):
                dont_use = chip.get('library', lib, 'asic', 'cells', 'dontuse',
                                    step=step, index=index)

            for lib_file in get_synthesis_libraries(lib):
                process_lib_file(libtype, lib, lib_file, dont_use)


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

    syn_corner = chip.get('tool', tool, 'task', task, 'var', 'synthesis_corner',
                          step=step, index=index)
    if syn_corner:
        return syn_corner[0]

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

    if isinstance(corner, (list)):
        corner = corner[0]

    return corner


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

    corner = get_synthesis_corner(chip)
    if corner is None:
        return None

    # if dff liberty file is not set, use the first liberty file defined
    delaymodel = chip.get('asic', 'delaymodel', step=step, index=index)
    for lib in chip.get('asic', 'logiclib', step=step, index=index):
        if not chip.valid('library', lib, 'output', corner, delaymodel):
            continue

        lib_files = chip.find_files('library', lib, 'output', corner, delaymodel,
                                    step=step, index=index)
        if len(lib_files) > 0:
            return lib_files[0]

    return None


def get_abc_period(chip):

    tool = 'yosys'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    abc_clock_period = chip.get('tool', tool, 'task', task, 'var', 'abc_clock_period',
                                step=step, index=index)
    if abc_clock_period:
        return abc_clock_period[0]

    period = None

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
                    clock_period = float(clock_period[0])

                    if period is None:
                        period = clock_period
                    else:
                        period = min(period, clock_period)

    if period is None and chip.valid('clock'):
        # get clock information from defined clocks
        for clock in chip.getkeys('clock'):
            if not chip.valid('clock', clock, 'period'):
                continue

            clock_period = float(chip.get('clock', clock, 'period'))
            if period is None:
                period = clock_period
            else:
                period = min(period, clock_period)

    if period is None:
        return None

    # need period in PS
    if chip.get('unit', 'time')[0] == 'n':
        period *= 1000

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
