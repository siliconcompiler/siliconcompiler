import os
import siliconcompiler

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

    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'

    # create a chip instance
    chip = siliconcompiler.Chip()
    # load configuration
    setup_tool(chip, step='spice', index='0')
    # write out results
    chip.writecfg(output)
