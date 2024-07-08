'''
VPR (Versatile Place and Route) is an open source CAD
tool designed for the exploration of new FPGA architectures and
CAD algorithms, at the packing, placement and routing phases of
the CAD flow. VPR takes, as input, a description of an FPGA
architecture along with a technology-mapped user circuit. It
then performs packing, placement, and routing to map the
circuit onto the FPGA. The output of VPR includes the FPGA
configuration needed to implement the circuit and statistics about
the final mapped design (eg. critical path delay, area, etc).

Documentation: https://docs.verilogtorouting.org/en/latest

Sources: https://github.com/verilog-to-routing/vtr-verilog-to-routing

Installation: https://github.com/verilog-to-routing/vtr-verilog-to-routing
'''

import os
import shutil
import json
import re
from siliconcompiler import sc_open, SiliconCompilerError
from siliconcompiler.tools._common import get_tool_task, record_metric


__block_file = "reports/block_usage.json"


######################################################################
# Make Docs
######################################################################
def make_docs(chip):
    chip.set('fpga', 'partname', 'example_arch_X005Y005')
    chip.load_target("fpgaflow_demo")
    setup_tool(chip)
    return chip


def setup_tool(chip, clobber=True):

    chip.set('tool', 'vpr', 'exe', 'vpr', clobber=clobber)
    chip.set('tool', 'vpr', 'vswitch', '--version')
    chip.set('tool', 'vpr', 'version', '>=8.1.0', clobber=clobber)

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)
    chip.set('tool', tool, 'task', task, 'regex', 'warnings', "^Warning",
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'regex', 'errors', "^Error",
             step=step, index=index, clobber=False)

    chip.set('tool', tool, 'task', task, 'var', 'enable_images', 'true',
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'var', 'enable_images',
             'true/false generate images of the design at the end of the task', field='help')

    part_name = chip.get('fpga', 'partname')
    for resource in ('vpr_registers', 'vpr_brams', 'vpr_dsps'):
        if not chip.valid('fpga', part_name, 'var', resource):
            continue
        if not chip.get('fpga', part_name, 'var', resource):
            continue
        chip.add('tool', tool, 'task', task, 'require', f'fpga,{part_name},var,{resource}',
                 step=step, index=index)


def runtime_options(chip):

    part_name = chip.get('fpga', 'partname')
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    options = []

    options.append(f"--write_block_usage {__block_file}")
    options.append("--outfile_prefix outputs/")

    if chip.valid('fpga', part_name, 'file', 'archfile') and \
       chip.get('fpga', part_name, 'file', 'archfile'):

        archs = chip.find_files('fpga', part_name, 'file', 'archfile',
                                step=None, index=None)

    else:
        archs = []

    if (len(archs) == 1):
        options.append(archs[0])
    elif (len(archs) == 0):
        raise SiliconCompilerError(
            "VPR requires an architecture file as one of its command line arguments",
            chip=chip)
    else:
        raise SiliconCompilerError(
            "Only one architecture XML file can be passed to VPR", chip=chip)

    threads = chip.get('tool', tool, 'task', task, 'threads', step=step, index=index)
    options.append(f"--num_workers {threads}")

    # For most architectures, constant nets need to be routed
    # like regular nets to be functionally correct (however inefficient
    # that might be...); these two options help control that
    options.append('--constant_net_method route')
    options.append('--const_gen_inference none')

    # If we allow VPR to sweep dangling primary I/Os and logic blocks
    # it can interfere with circuit debugging; so disable that
    options.append('--sweep_dangling_primary_ios off')
    options.append('--sweep_constant_primary_outputs off')
    options.append('--sweep_dangling_blocks off')

    # Explicitly specify the clock modeling type in the part driver
    # to avoid ambiguity and future-proof against new VPR clock models
    clock_model = chip.get('fpga', part_name, 'var', 'vpr_clock_model')
    if not clock_model:
        raise SiliconCompilerError(f'no clock model defined for {part_name}', chip=chip)
    else:
        selected_clock_model = clock_model[0]
        # When dedicated networks are used, tell VPR to use the two-stage router,
        # otherwise not.
        if (selected_clock_model == 'ideal'):
            options.append(f'--clock_modeling {selected_clock_model}')
        elif (selected_clock_model == 'route'):
            options.append(f'--clock_modeling {selected_clock_model}')
        elif (selected_clock_model == 'dedicated_network'):
            options.append(f'--clock_modeling {selected_clock_model}')
            options.append('--two_stage_clock_routing')
        else:
            raise SiliconCompilerError(
                'vpr_clock model must be set to ideal, route, or dedicated_clock_network',
                chip=chip)

    if 'sdc' in chip.getkeys('input', 'constraint'):
        sdc_file = find_single_file(chip, 'input', 'constraint', 'sdc',
                                    step=step, index=index,
                                    file_not_found_msg="SDC file not found")
        if (sdc_file is not None):
            sdc_arg = f"--sdc_file {sdc_file}"
            options.append(sdc_arg)
    else:
        options.append("--timing_analysis off")

    # Per the scheme implemented in the placement pre-process step,
    # if a constraints file exists it will always be in the auto_constraints()
    # location:
    if (os.path.isfile(auto_constraints())):
        pin_constraint_arg = f"--read_vpr_constraints {auto_constraints()}"
        options.append(pin_constraint_arg)

    # Routing graph XML:
    rr_graph = find_single_file(chip, 'fpga', part_name, 'file', 'graphfile',
                                step=None, index=None,
                                file_not_found_msg="VPR RR Graph not found")
    if (rr_graph is None):
        chip.logger.info("No VPR RR graph file specified")
        chip.logger.info("Routing architecture will come from architecture XML file")
    else:
        options.append("--read_rr_graph " + rr_graph)

    # ***NOTE: For real FPGA chips you need to specify the routing channel
    #          width explicitly.  VPR requires an explicit routing channel
    #          with when --read_rr_graph is used (typically the case for
    #          real chips).  Otherwise VPR performs a binary search for
    #          the minimum routing channel width that the circuit fits in.
    # Given the above, it may be appropriate to couple these variables somehow,
    # but --route_chan_width CAN be used by itself.
    num_routing_channels = chip.get('fpga', part_name, 'var', 'channelwidth')

    if (len(num_routing_channels) == 0):
        raise SiliconCompilerError("Number of routing channels not specified", chip=chip)
    elif (len(num_routing_channels) == 1):
        options.append("--route_chan_width " + num_routing_channels[0])
    elif (len(num_routing_channels) > 1):
        raise SiliconCompilerError(
            "Only one routing channel width argument can be passed to VPR", chip=chip)

    return options


############################
# Get common graphics files
############################

def get_common_graphics(chip):

    design = chip.top()

    graphics_commands = []

    # set_draw_block_text 1 displays the label for various blocks in the design
    # set_draw_block_outlines 1 displays the outline/boundary for various blocks in the design
    # save_graphics saves the block diagram as a png/svg/pdf
    # Refer: https://docs.verilogtorouting.org/en/latest/vpr/command_line_usage/#graphics-options
    graphics_commands.append("set_draw_block_text 1; " +
                             "set_draw_block_outlines 1; " +
                             f"save_graphics reports/{design}_place.png;")

    return graphics_commands


################################
# Wrapper around find files to
# help with error checking that
# only a single file is found
################################

def find_single_file(chip, *keypath, step=None, index=None, file_not_found_msg="File not found"):

    if chip.valid(*keypath) and chip.get(*keypath, step=step, index=index):
        file_list = chip.find_files(*keypath, step=step, index=index)
    else:
        file_list = []

    if (len(file_list) == 1):
        return file_list[0]
    elif (len(file_list) == 0):
        chip.logger.info(file_not_found_msg)
        return None
    else:
        raise SiliconCompilerError("Only one file of this type can be passed to VPR", chip=chip)


################################
# Version Check
################################


def parse_version(stdout):

    # Example output of vpr --version:
    # Note that blank comment lines in this example
    # represent newlines printed by vpr --version

    # VPR FPGA Placement and Routing.
    # Version: 8.1.0-dev+c4156f225
    # Revision: v8.0.0-7887-gc4156f225
    # Compiled: 2023-06-14T17:32:05
    # Compiler: GNU 9.4.0 on Linux-5.14.0-1059-oem x86_64
    # Build Info: release IPO VTR_ASSERT_LEVEL=2
    #
    # University of Toronto
    # verilogtorouting.org
    # vtr-users@googlegroups.com
    # This is free open source code under MIT license.
    #
    #
    return stdout.split()[6]


def normalize_version(version):
    if '-' in version:
        return version.split('-')[0]
    else:
        return version


def auto_constraints():
    return 'inputs/sc_constraints.xml'


def vpr_post_process(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    if os.path.exists('packing_pin_util.rpt'):
        shutil.move('packing_pin_util.rpt', 'reports')

    part_name = chip.get('fpga', 'partname')
    dff_cells = []
    if chip.valid('fpga', part_name, 'var', 'vpr_registers'):
        dff_cells = chip.get('fpga', part_name, 'var', 'vpr_registers')
    brams_cells = []
    if chip.valid('fpga', part_name, 'var', 'vpr_brams'):
        brams_cells = chip.get('fpga', part_name, 'var', 'vpr_brams')
    dsps_cells = []
    if chip.valid('fpga', part_name, 'var', 'vpr_dsps'):
        dsps_cells = chip.get('fpga', part_name, 'var', 'vpr_dsps')

    stat_extract = re.compile(r'  \s*(.*)\s*:\s*([0-9]+)')
    lut_match = re.compile(r'([0-9]+)-LUT')
    route_length = re.compile(r'	Total wirelength: ([0-9]+)')
    log_file = f'{step}.log'
    mdata = {
        "registers": 0,
        "luts": 0,
        "dsps": 0,
        "brams": 0
    }
    with sc_open(log_file) as f:
        in_stats = False
        for line in f:
            if in_stats:
                if not line.startswith("  "):
                    in_stats = False
                    continue
                data = stat_extract.findall(line)
                if data:
                    dtype, value = data[0]
                    dtype = dtype.strip()
                    value = int(value)

                    if dtype == "Blocks":
                        record_metric(chip, step, index, "cells", value, log_file)
                    elif dtype == "Nets":
                        record_metric(chip, step, index, "nets", value, log_file)
                    elif dtype in dff_cells:
                        mdata["registers"] += value
                    elif dtype in dsps_cells:
                        mdata["dsps"] += value
                    elif dtype in brams_cells:
                        mdata["brams"] += value
                    else:
                        lut_type = lut_match.findall(dtype)
                        if lut_type:
                            if int(lut_type[0]) == 0:
                                pass
                            else:
                                mdata["luts"] += value
            else:
                if line.startswith("Circuit Statistics:"):
                    in_stats = True
                route_len_data = route_length.findall(line)
                if route_len_data:
                    # Fake the unit since this is meaningless for the FPGA
                    units = chip.get('metric', 'wirelength', field='unit')
                    record_metric(chip, step, index, 'wirelength',
                                  int(route_len_data[0]),
                                  log_file,
                                  source_unit=units)

    for metric, value in mdata.items():
        record_metric(chip, step, index, metric, value, log_file)

    if os.path.exists(__block_file):
        with sc_open(__block_file) as f:
            data = json.load(f)

            if "num_nets" in data and chip.get('metric', 'nets', step=step, index=index) is None:
                record_metric(chip, step, index, "nets", int(data["num_nets"]), __block_file)

            io = 0
            if "input_pins" in data:
                io += int(data["input_pins"])
            if "output_pins" in data:
                io += int(data["output_pins"])

            record_metric(chip, step, index, "pins", io, __block_file)


##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("vpr.json")
