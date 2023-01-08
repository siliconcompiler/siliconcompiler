import os
import re
import json
import shutil
import importlib
from jinja2 import Template
import siliconcompiler
import siliconcompiler.tools.yosys.markDontUse as markDontUse

######################################################################
# Make Docs
######################################################################

def make_docs():
    '''
    Yosys is a framework for RTL synthesis that takes synthesizable
    Verilog-2005 design and converts it to BLIF, EDIF, BTOR, SMT,
    Verilog netlist etc. The tool supports logical synthesis and
    tech mapping to ASIC standard cell libraries, FPGA architectures.
    In addition it has built in formal methods for property and
    equivalence checking.

    Documentation: http://www.clifford.at/yosys/documentation.html

    Sources: https://github.com/YosysHQ/yosys

    Installation: https://github.com/YosysHQ/yosys

    '''

    chip = siliconcompiler.Chip('<design>')
    chip.set('arg','step', 'syn')
    chip.set('arg','index', '<index>')
    setup(chip)
    return chip

################################
# Setup Tool (pre executable)
################################

def setup(chip):
    ''' Tool specific function to run before step execution
    '''

    # If the 'lock' bit is set, don't reconfigure.
    tool = 'yosys'
    refdir = 'tools/'+tool
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    # Standard Setup
    chip.set('tool', tool, 'exe', 'yosys')
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=0.24', clobber=False)
    chip.set('tool', tool, 'format', 'tcl', clobber=False)
    chip.set('tool', tool, 'option', step, index, '-c', clobber=False)
    chip.set('tool', tool, 'refdir', step, index, refdir, clobber=False)

    if re.search(r'syn', step):
        script = 'sc_syn.tcl'
    elif re.search(r'lec', step):
        script = 'sc_lec.tcl'
    else:
        # Emit a warning for unsupported yosys step, but allow execution to proceed.
        # Users can configure their own flows involving yosys, but they will be responsible for
        # setting appropriate schema values, including 'script'.
        script = ''
        chip.logger.warning(f'Unsupported yosys step: {step}.')

    chip.set('tool', tool, 'script', step, index, script, clobber=False)

    design = chip.top()

    # Input/output requirements
    if step.startswith('syn'):
        # TODO: Our yosys script can also accept uhdm or ilang files. How do we
        # represent a set of possible inputs where you must pick one?
        chip.set('tool', tool, 'input', step, index, design + '.v')
        chip.set('tool', tool, 'output', step, index, design + '.vg')
        chip.add('tool', tool, 'output', step, index, design + '_netlist.json')
        chip.add('tool', tool, 'output', step, index, design + '.blif')
    elif step == 'lec':
        if (not chip.valid('input', 'netlist') or
            not chip.get('input', 'netlist')):
            chip.set('tool', tool, 'input', step, index, design + '.vg')
        if not chip.get('input', 'verilog'):
            # TODO: Not sure this logic makes sense? Seems like reverse of
            # what's in TCL
            chip.set('tool', tool, 'input', step, index, design + '.v')

    # Schema requirements
    if chip.get('option', 'mode') == 'asic':
        chip.add('tool', tool, 'require', step, index, ",".join(['asic', 'logiclib']))

        delaymodel = chip.get('asic', 'delaymodel')
        syn_corner = get_synthesis_corner(chip)
        # add synthesis corner information
        if syn_corner is None:
            chip.add('tool', tool, 'require', step, index, ",".join(['tool', tool, 'var', step, index, 'synthesis_corner']))
        if get_dff_liberty_file(chip) is None:
            chip.add('tool', tool, 'require', step, index, ",".join(['tool', tool, 'var', step, index, 'dff_liberty']))

        if syn_corner is not None:
            # add timing library requirements
            for lib in chip.get('asic', 'logiclib'):
                # mandatory for logiclibs
                chip.add('tool', tool, 'require', step, index, ",".join(['library', lib, 'model', 'timing', delaymodel, syn_corner]))

            for lib in chip.get('asic', 'macrolib'):
                # optional for macrolibs
                if not chip.valid('library', lib, 'model', 'timing', delaymodel, syn_corner):
                    continue

                chip.add('tool', tool, 'require', step, index, ",".join(['library', lib, 'model', 'timing', delaymodel, syn_corner]))

        mainlib = chip.get('asic', 'logiclib')[0]
        # set default control knobs
        for option, value, additional_require in [('flatten', "True", None),
                                                  ('autoname', "True", None),
                                                  ('map_adders', "False", ['library', mainlib, 'asic', 'file', tool, 'addermap'])]:
            chip.set('tool', tool, 'var', step, index, option, value, clobber=False)
            chip.add('tool', tool, 'require', step, index, ",".join(['tool', tool, 'var', step, index, option]))
            if additional_require is not None and chip.get('tool', tool, 'var', step, index, option)[0] == "True":
                chip.add('tool', tool, 'require', step, index, ",".join(additional_require))

        # copy techmapping from libraries
        for lib in chip.get('asic', 'logiclib') + chip.get('asic', 'macrolib'):
            if not chip.valid('library', lib, 'asic', 'file', tool, 'techmap'):
                continue
            for techmap in chip.find_files('library', lib, 'asic', 'file', tool, 'techmap'):
                if techmap is None:
                    continue
                chip.add('tool', tool, 'var', step, index, 'techmap', techmap)

        chip.set('tool', tool, 'var', step, index, 'synthesis_corner', get_synthesis_corner(chip), clobber=False)
        chip.set('tool', tool, 'var', step, index, 'dff_liberty', get_dff_liberty_file(chip), clobber=False)
        chip.add('tool', tool, 'require', step, index, ",".join(['tool', tool, 'var', step, index, 'synthesis_corner']))
        chip.add('tool', tool, 'require', step, index, ",".join(['tool', tool, 'var', step, index, 'dff_liberty']))

        # Constants needed by yosys, do not allow overriding of values so force clobbering
        chip.set('tool', tool, 'var', step, index, 'dff_liberty_file', "inputs/sc_dff_library.lib", clobber=True)
        chip.set('tool', tool, 'var', step, index, 'abc_constraint_file', "inputs/sc_abc.constraints", clobber=True)

        abc_driver = get_abc_driver(chip)
        if abc_driver:
            chip.set('tool', tool, 'var', step, index, 'abc_constraint_driver', abc_driver, clobber=False)
        abc_clock_period = get_abc_period(chip)
        if abc_clock_period:
            chip.set('tool', tool, 'var', step, index, 'abc_clock_period', str(abc_clock_period), clobber=False)
            chip.add('tool', tool, 'require', step, index, ",".join(['tool', tool, 'var', step, index, 'abc_clock_period']))

        # document parameters
        chip.set('tool', tool, 'var', step, index, 'preserve_modules', 'List of modules in input files to prevent flatten from "flattening"', field='help')
        chip.set('tool', tool, 'var', step, index, 'flatten', 'True/False, invoke synth with the -flatten option', field='help')
        chip.set('tool', tool, 'var', step, index, 'autoname', 'True/False, call autoname to rename wires based on registers', field='help')
        chip.set('tool', tool, 'var', step, index, 'map_adders', 'False/path to map_adders, techmap adders in Yosys', field='help')
        chip.set('tool', tool, 'var', step, index, 'synthesis_corner', 'Timing corner to use for synthesis', field='help')
        chip.set('tool', tool, 'var', step, index, 'dff_liberty', 'Liberty file to use for flip-flop mapping, if not specified the first in the logiclib is used', field='help')
        chip.set('tool', tool, 'var', step, index, 'abc_constraint_driver', 'Buffer that drives the abc techmapping, defaults to first buffer specified', field='help')
        chip.set('tool', tool, 'var', step, index, 'abc_constraint_load', 'Capacitive load for the abc techmapping in fF, if not specified it will not be used', field='help')
        chip.set('tool', tool, 'var', step, index, 'abc_clock_period', 'Clock period to use for synthesis in ps, if more than one clock is specified, the smallest period is used.', field='help')
        chip.set('tool', tool, 'var', step, index, 'abc_clock_derating', 'Used to derate the clock period to further constrain the clock, values between 0 and 1', field='help')

    else:
        chip.add('tool', tool, 'require', step, index, ",".join(['fpga', 'partname']))

    # Setting up regex patterns
    chip.set('tool', tool, 'regex', step, index, 'warnings', "Warning:", clobber=False)
    chip.set('tool', tool, 'regex', step, index, 'errors', "^ERROR", clobber=False)

    # Reports
    for metric in ('cells', 'nets', 'pins'):
        chip.set('tool', tool, 'report', step, index, metric, "reports/stat.json")
    for metric in ('cellarea', 'errors', 'warnings', 'cellarea', 'drvs', 'coverage', 'security',
                   'luts', 'dsps', 'brams', 'registers', 'buffers'):
        chip.set('tool', tool, 'report', step, index, metric, f"{step}.log")

#############################################
# Runtime pre processing
#############################################

def pre_process(chip):

    tool = 'yosys'
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    # copy the VPR library to the yosys input directory and render the placeholders
    if chip.get('fpga', 'arch'):
        create_vpr_lib(chip)
        return

    if chip.get('option', 'mode') == 'asic':
        prepare_synthesis_libraries(chip)
        create_abc_synthesis_constraints(chip)
        return

################################
# Version Check
################################

def parse_version(stdout):
    # Yosys 0.9+3672 (git sha1 014c7e26, gcc 7.5.0-3ubuntu1~18.04 -fPIC -Os)
    return stdout.split()[1]

def normalize_version(version):
    # Replace '+', which represents a "local version label", with '-', which is
    # an "implicit post release number".
    return version.replace('+', '-')

################################
# Post_process (post executable)
################################
def post_process(chip):
    ''' Tool specific function to run after step execution
    '''

    tool = 'yosys'
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    # Extracting
    if step.startswith('syn'):
        #TODO: looks like Yosys exits on error, so no need to check metric
        chip.set('metric', step, index, 'errors', 0, clobber=True)
        with open("reports/stat.json", 'r') as f:
            metrics = json.load(f)
            if "design" in metrics:
                metrics = metrics["design"]

            if "area" in metrics:
                chip.set('metric', step, index, 'cellarea', float(metrics["area"]), clobber=True)
            if "num_cells" in metrics:
                chip.set('metric', step, index, 'cells', int(metrics["num_cells"]), clobber=True)

        registers = None
        with open(f"{step}.log", 'r') as f:
            for line in f:
                area_metric = re.findall(r"^SC_METRIC: area: ([0-9.]+)", line)
                if area_metric:
                    chip.set('metric', step, index, 'cellarea', float(area_metric[0]), clobber=True)
                line_registers = re.findall(r"^\s*mapped ([0-9]+) \$_DFF.*", line)
                if line_registers:
                    if registers is None:
                        registers = 0
                    registers += int(line_registers[0])
        if registers is not None:
            chip.set('metric', step, index, 'registers', registers, clobber=True)
    elif step == 'lec':
        with open(step + ".log") as f:
            for line in f:
                if line.endswith('Equivalence successfully proven!\n'):
                    chip.set('metric', step, index, 'drvs', 0, clobber=True)
                    continue

                errors = re.search(r'Found a total of (\d+) unproven \$equiv cells.', line)
                if errors is not None:
                    num_errors = int(errors.group(1))
                    chip.set('metric', step, index, 'drvs', num_errors, clobber=True)


################################
# copy and render the VPR library
################################
def create_vpr_lib(chip):

    #copy the VPR techmap library to the input directory
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    src = f"{chip.scroot}/tools/yosys/vpr_yosyslib"
    dst = f"{chip._getworkdir()}/{step}/{index}/inputs/vpr_yosyslib"

    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    spec = importlib.util.spec_from_file_location("utils", f"{chip.scroot}/utils.py")
    imported = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(imported)

    Arch = getattr(imported, 'Arch')
    arch = Arch(chip.get('fpga', 'arch')[0])
    max_lut_size = arch.find_max_lut_size()
    max_mem_addr_width = arch.find_memory_addr_width()

    #render the template placeholders
    data = {
        "max_lut_size": max_lut_size,
        "memory_addr_width": max_mem_addr_width,
        "lib_dir": dst,
        "min_hard_adder_size": "1",
        "min_hard_mult_size": "3"
    }

    for _, _, lib_files in os.walk(dst):
        for file_name in lib_files:
            file = f"{dst}/{file_name}"
            print(file)
            with open(file) as template_f:
                template = Template(template_f.read())
            with open(file, "w") as rendered_f:
                rendered_f.write(template.render(data))

################################
# mark cells dont use and format liberty files for yosys and abc
################################
def prepare_synthesis_libraries(chip):

    tool = 'yosys'
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    corner = chip.get('tool', tool, 'var', step, index, 'synthesis_corner')[0]
    delaymodel = chip.get('asic', 'delaymodel')

    # mark dff libery file with dont use
    dff_liberty_file = chip.get('tool', tool, 'var', step, index, 'dff_liberty')[0]
    dff_dont_use = []
    for lib in chip.get('asic', 'logiclib'):
        ignore = chip.get('library', lib, 'asic', 'cells', 'ignore')
        if dff_liberty_file in chip.find_files('library', lib, 'model', 'timing', delaymodel, corner):
            # if we have the exact library, use those ignores, otherwise continue to build full list
            dff_dont_use = ignore
            break

        dff_dont_use.extend(ignore)

    markDontUse.processLibertyFile(dff_liberty_file, chip.get('tool', tool, 'var', step, index, 'dff_liberty_file')[0], dff_dont_use, chip.get('option', 'quiet'))

    #### Generate synthesis_libraries and synthesis_macro_libraries for Yosys use

    # mark libs with dont_use since ABC cannot get this information via its commands
    # this also ensures the liberty files have been decompressed and corrected formatting
    # issues that generally cannot be handled by yosys or yosys-abc
    def get_synthesis_libraries(lib):
        if chip.valid('library', lib, 'asic', 'file', 'yosys', 'synthesis_libraries'):
            synthesis_libraries = chip.find_files('library', lib, 'asic', 'file', 'yosys', 'synthesis_libraries')
        elif chip.valid('library', lib, 'model', 'timing', delaymodel, corner):
            synthesis_libraries = chip.find_files('library', lib, 'model', 'timing', delaymodel, corner)
        else:
            synthesis_libraries = []

        return synthesis_libraries

    def process_lib_file(libtype, lib, lib_file, dont_use):
        input_base_name = os.path.splitext(os.path.basename(lib_file))[0]
        output_file = f"inputs/sc_{libtype}_{lib}_{input_base_name}.lib"
        markDontUse.processLibertyFile(lib_file, output_file, dont_use, chip.get('option', 'quiet'))

        var_name = 'synthesis_libraries'
        if (libtype == "macrolib"):
            var_name = 'synthesis_libraries_macros'

        chip.add('tool', tool, 'var', step, index, var_name, output_file)

    for libtype in ('logiclib', 'macrolib'):
        for lib in chip.get('asic', libtype):
            dont_use = chip.get('library', lib, 'asic', 'cells', 'ignore')

            for lib_file in get_synthesis_libraries(lib):
                process_lib_file(libtype, lib, lib_file, dont_use)

def create_abc_synthesis_constraints(chip):

    tool = 'yosys'
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    abc_driver = None
    if chip.valid('tool', tool, 'var', step, index, 'abc_constraint_driver'):
        abc_driver = chip.get('tool', tool, 'var', step, index, 'abc_constraint_driver')
        if abc_driver:
            abc_driver = abc_driver[0]

    abc_load = None
    if chip.valid('tool', tool, 'var', step, index, 'abc_constraint_load'):
        abc_load = chip.get('tool', tool, 'var', step, index, 'abc_constraint_load')
        if abc_load:
            abc_load = float(abc_load[0])

    if not abc_driver and not abc_load:
        # either is set so nothing to do
        return

    with open(chip.get('tool', tool, 'var', step, index, 'abc_constraint_file')[0], "w") as f:
        if abc_driver:
            f.write(f"set_driving_cell {abc_driver}\n")
        if abc_load:
            # convert to fF
            if chip.get('unit', 'capacitance')[0] == 'p':
                abc_load *= 1000
            f.write(f"set_load {abc_load}\n")

def get_synthesis_corner(chip):

    tool = 'yosys'
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    if chip.valid('tool', tool, 'var', step, index, 'synthesis_corner'):
        return chip.get('tool', tool, 'var', step, index, 'synthesis_corner')[0]

    # determine corner based on setup corner from constraints
    corner = None
    for constraint in chip.getkeys('constraint', 'timing'):
        if "setup" in chip.get('constraint', 'timing', constraint, 'check') and not corner:
            corner = chip.get('constraint', 'timing', constraint, 'libcorner')

    if corner is None:
        # try getting it from first constraint with a valid libcorner
        for constraint in chip.getkeys('constraint', 'timing'):
            if chip.valid('constraint', 'timing', constraint, 'libcorner') and not corner:
                corner = chip.get('constraint', 'timing', constraint, 'libcorner')

    if isinstance(corner, (list)):
        corner = corner[0]

    return corner

def get_dff_liberty_file(chip):

    tool = 'yosys'
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    if chip.valid('tool', tool, 'var', step, index, 'dff_liberty'):
        return chip.get('tool', tool, 'var', step, index, 'dff_liberty')[0]

    corner = get_synthesis_corner(chip)
    if corner is None:
        return None

    # if dff liberty file is not set, use the first liberty file defined
    delaymodel = chip.get('asic', 'delaymodel')
    for lib in chip.get('asic', 'logiclib'):
        if not chip.valid('library', lib, 'model', 'timing', delaymodel, corner):
            continue

        lib_files = chip.find_files('library', lib, 'model', 'timing', delaymodel, corner)
        if len(lib_files) > 0:
            return lib_files[0]

    return None

def get_abc_period(chip):

    tool = 'yosys'
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    if chip.valid('tool', tool, 'var', step, index, 'abc_clock_period'):
        abc_clock_period = chip.get('tool', tool, 'var', step, index, 'abc_clock_period')
        if abc_clock_period:
            return abc_clock_period[0]

    period = None
    # get clock information from sdc files
    if chip.valid('input', 'sdc'):
        for sdc in chip.find_files('input', 'sdc'):
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

    if chip.valid('tool', tool, 'var', step, index, 'abc_clock_derating'):
        derating = float(chip.get('tool', tool, 'var', step, index, 'abc_clock_derating')[0])
        if derating > 1:
            chip.logger.warning("abc_clock_derating is greater than 1.0")
        elif derating > 0:
            period *= (1.0 - derating)
        else:
            chip.logger.error("abc_clock_derating is negative")

    return int(period)

def get_abc_driver(chip):

    tool = 'yosys'
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    abc_driver = None
    if chip.valid('tool', tool, 'var', step, index, 'abc_constraint_driver'):
        abc_driver = chip.get('tool', tool, 'var', step, index, 'abc_constraint_driver')[0]

    if abc_driver is None:
        # get the first driver defined in the logic lib
        for lib in chip.get('asic', 'logiclib'):
            if chip.valid('library', lib, 'asic', 'cells', 'driver') and not abc_driver:
                abc_driver = chip.get('library', lib, 'asic', 'cells', 'driver')[0]

    return abc_driver

##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("yosys.json")
