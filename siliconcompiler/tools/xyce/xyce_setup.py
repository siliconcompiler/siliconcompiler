import os
import siliconcompiler


#####################################################################
# Make Docs
#####################################################################

def make_docs():
    '''Xyce is a high performance SPICE-compatible circuit simulator.

    Xyce (zīs, rhymes with “spice”) is an open source,
    SPICE-compatible high-performance analog circuit simulator,
    capable of solving extremely large circuit problems by
    supporting large-scale parallel computing platforms. It also
    supports serial execution on all common desktop platforms,
    and small-scale parallel runs on Unix-like systems.

    Installation Instructions:

    Source code:
    * https://github.com/Xyce/Xyce

    Documentation:
    * https://xyce.sandia.gov

    '''

    chip = siliconcompiler.Chip()
    setup_tool(chip,'spice','<index>')
    return chip

################################
# Setup Tool (pre executable)
################################
def setup_tool(chip, step, index):


     tool = 'xyce'
     refdir = 'siliconcompiler/tools' + tool
     clobber = False

     chip.set('eda', tool, step, index, 'exe', tool, clobber=clobber)
     chip.set('eda', tool, step, index, 'copy', 'false', clobber=clobber)
     chip.set('eda', tool, step, index, 'vendor', tool, clobber=clobber)
     chip.set('eda', tool, step, index, 'version', '0.0', clobber=clobber)
     chip.set('eda', tool, step, index, 'threads', os.cpu_count(), clobber=clobber)

################################
# Post_process (post executable)
################################
def post_process(chip, step):
    ''' Tool specific function to run after step execution
    '''

    #TODO: return error code
    return 0

##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.writecfg("xyce.json")
