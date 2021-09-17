import os
import siliconcompiler


#####################################################################
# Make Docs
#####################################################################

def make_docs():
    '''
    Xyce is a high performance SPICE-compatible circuit simulator
    capable capable of solving extremely large circuit problems by
    supporting large-scale parallel computing platforms. It also
    supports serial execution on all common desktop platforms,
    and small-scale parallel runs on Unix-like systems.

    Documentation: https://xyce.sandia.gov/documentation

    Sources: https://github.com/Xyce/Xyce

    Installation: https://xyce.sandia.gov/documentation/BuildingGuide.html

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
