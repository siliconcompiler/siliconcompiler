import os
import siliconcompiler

######################################################################
# Make Docs
######################################################################

def make_docs():
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

    .. warning::
       Work in progress (not ready for use)
    '''

    chip = siliconcompiler.Chip()
    chip.set('arg','step', 'apr')
    chip.set('arg','index', '<index>')
    chip.set('design', '<design>')
    setup_tool(chip)
    return chip

################################
# Setup Tool (pre executable)
################################
def setup_tool(chip):

     tool = 'vpr'
     refdir = 'tools/'+tool
     step = chip.get('arg','step')
     index = chip.get('arg','index')

     chip.set('eda', tool, step, index, 'exe', tool, clobber=False)
     chip.set('eda', tool, step, index, 'threads', os.cpu_count(), clobber=False)
     chip.set('eda', tool, step, index, 'version', '0.0', clobber=False)

     topmodule = chip.get('design')
     blif = "inputs/" + topmodule + ".blif"

     options = []
     for arch in chip.get('fpga','arch'):
          options.append(arch)

     options.append(blif)

     chip.add('eda', tool, step, index, 'option', options)

################################
# Post_process (post executable)
################################

def post_process(chip):
    ''' Tool specific function to run after step execution
    '''
    step = chip.get('arg','step')
    index = chip.get('arg','index')

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
    setup_tool(chip, step='apr', index='0')
    # write out results
    chip.writecfg(output)
