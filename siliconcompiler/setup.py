import sys
import importlib
from siliconcompiler.schema import schema_istrue
from siliconcompiler.schema import schema_path

#############################
#Initial Setup
############################
def setup_target(chip):
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

        # EDA Flow is hard coded?
        for step in (['import']):
            setup_step(chip, step, "verilator")

        for step in (['syn']):
            setup_step(chip, step, "yosys")

        for step in (['floorplan', 'place', 'cts', 'route', 'dfm']):
            if chip.get('mode')[-1] == 'fpga':
                setup_step(chip, step, "nextpnr")
            else:
                setup_step(chip, step, "openroad")

        for step in (['export']):
            if chip.get('mode')[-1] == 'fpga':
                setup_step(chip, step, "icepack")
            else:
                setup_step(chip, step, "klayout")
    else:
        if os.getenv('SCPATH') == None:
            chip.logger.error('Environment variable $SCPATH has \
            not been set, required for closed targets')
            sys.exit()
        module = importlib.import_module("external_target")
        setup_target = getattr(module,"setup_target")
        setup_target(chip, target)

#helper fucntion
def setup_step(chip, step, vendor):
    edadir = "eda." + vendor
    module = importlib.import_module('.'+vendor, package=edadir)
    setup_tool = getattr(module,"setup_tool")
    setup_tool(chip,step)

#############################
# Runtime Options
############################

def setup_cmd(chip,step):

    #Set Executable
    exe = chip.cfg['flow'][step]['exe']['value'][-1] #scalar
    cmd_fields = [exe]

    #Dynamically generate options
    vendor = chip.cfg['flow'][step]['vendor']['value'][-1]
    tool  = chip.cfg['flow'][step]['exe']['value'][-1]
    module = importlib.import_module('.'+tool,
                                     package="eda." + vendor)
    setup_options = getattr(module,"setup_options")
    options = setup_options(chip,step)

    #Add options to cmd list
    cmd_fields.extend(options)        

    #Resolve Paths
    if schema_istrue(chip.cfg['flow'][step]['copy']['value']):
        for value in chip.cfg['flow'][step]['script']['value']:
            abspath = schema_path(value)
            cmd_fields.append(abspath)
    else:
        for value in chip.cfg['flow'][step]['script']['value']:
            cmd_fields.append(value)      

    #Piping to log file
    logfile = exe + ".log"
    if schema_istrue(chip.cfg['quiet']['value']):
        cmd_fields.append("> " + logfile)
    else:
        cmd_fields.append("| tee " + logfile)
    cmd = ' '.join(cmd_fields)

    return cmd

   
