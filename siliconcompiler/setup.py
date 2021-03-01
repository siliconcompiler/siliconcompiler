import sys
import importlib
from siliconcompiler.schema import schema_istrue
from siliconcompiler.schema import schema_path

#############################
#Initial Setup
############################
def find_target(chip):
    ''' Finds the target setup files based on a single string name.
    A select set of built targets can be set, otherwise the target
    is search using the SCPATH environment variable.
    '''

    target = chip.cfg['target']['value'][-1]

    if target in ('freepdk45', 'asap7', 'skywater130'):            
        #Dynamic PDK Module Setup
        pdkdir = "foundry.virtual." + target + ".pdk"
        module = importlib.import_module('.sc_pdk', package=pdkdir)
        setup_pdk = getattr(module,"setup_pdk")
        setup_pdk(chip)

        #Dynamic LIB Module Setup
        libsdir = "foundry.virtual." + target + ".libs"
        module = importlib.import_module('.sc_libs', package=libsdir)
        setup_libs = getattr(module,"setup_libs")
        setup_libs(chip)

        # EDA Flow is hard coded for builtin
        for stage in (['import']):
            setup_stage(chip, stage, "verilator")

        for stage in (['syn']):
            setup_stage(chip, stage, "yosys")

        for stage in (['floorplan', 'place', 'cts', 'route', 'signoff']):
            if chip.cfg['mode'] == 'fpga' :
                setup_stage(chip, stage, "vpr")
            else:
                setup_stage(chip, stage, "openroad")

        for stage in (['export']):
            if chip.cfg['mode'] == 'fpga' :
                setup_stage(chip, stage, "vpr")
            else:
                setup_stage(chip, stage, "klayout")
    else:
        if os.getenv('SCPATH') == None:
            chip.logger.error('Environment variable $SCPATH has \
            not been set, required for closed targets')
            sys.exit()
        module = importlib.import_module(target)
        setup_target = getattr(module,"setup_target")
        setup_target(chip)

#helper fucntion
def setup_stage(chip, stage, vendor):
    edadir = "eda." + vendor
    module = importlib.import_module('.'+vendor, package=edadir)
    setup_tool = getattr(module,"setup_tool")
    setup_tool(chip,stage)

#############################
# Runtime Options
############################

def setup_cmd(chip,stage):

    #Set Executable
    exe = chip.cfg['tool'][stage]['exe']['value'][-1] #scalar
    cmd_fields = [exe]

    #Dynamically generate options
    vendor = chip.cfg['tool'][stage]['vendor']['value'][-1]
    tool  = chip.cfg['tool'][stage]['exe']['value'][-1]
    module = importlib.import_module('.'+tool,
                                     package="eda." + vendor)
    setup_options = getattr(module,"setup_options")
    options = setup_options(chip,stage)

    #Add options to cmd list
    cmd_fields.extend(options)        

    #Resolve Paths
    if schema_istrue(chip.cfg['tool'][stage]['copy']['value']):
        for value in chip.cfg['tool'][stage]['script']['value']:
            abspath = schema_path(value)
            cmd_fields.append(abspath)
    else:
        for value in chip.cfg['tool'][stage]['script']['value']:
            cmd_fields.append(value)      

    #Piping to log file
    logfile = exe + ".log"
    if schema_istrue(chip.cfg['quiet']['value']):
        cmd_fields.append("> " + logfile)
    else:
        cmd_fields.append("| tee " + logfile)
    cmd = ' '.join(cmd_fields)

    return cmd

   
############################
# Post Process Command
############################

def post_cmd(chip,stage, vendor):
    vendor = chip.cfg['tool'][stage]['vendor']['value'][-1]
    tool  = chip.cfg['tool'][stage]['exe']['value'][-1]
    module = importlib.import_module('.'+tool,
                                     package="eda." + vendor)
    
    post_process = getattr(module,"post_process")
    post_process(chip,stage)
    
