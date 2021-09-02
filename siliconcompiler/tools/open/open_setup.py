import os
import platform
import siliconcompiler

################################
# Setup Tool (pre executable)
################################

def setup_tool(chip, step, index):
    ''' Tool specific function to run before step execution
    '''

    chip.logger.debug("Setting up File Open Command")

    tool = 'open'
    chip.set('eda', tool, step, '0', 'format', 'cmdline')
    chip.set('eda', tool, step, '0', 'copy', 'false')
    if platform.system() == 'Linux':
        chip.set('eda', tool, step, '0', 'exe', 'xdg-open')
    elif platform.system() == 'Darwin':
        chip.set('eda', tool, step, '0', 'exe', 'open')

################################
# Post_process (post executable)
################################
def post_process(chip, step, index):
    ''' Tool specific function to run after step execution
    '''
    return 0

##################################################
if __name__ == "__main__":

    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'

    # create a chip instance
    chip = siliconcompiler.Chip()
    # load configuration
    setup_tool(chip, step='open', index=0)
    # write out results
    chip.writecfg(output)
