import os
import siliconcompiler

######################################################################
# Make Docs
######################################################################

def make_docs():
    '''VPR is a universal FPGA place and route tool.

    VPR (Versatile Place and Route) is an open source CAD
    tool designed for the exploration of new FPGA architectures and
    CAD algorithms, at the packing, placement and routing phases of
    the CAD flow. Since its public introduction, VPR has been
    used extensively in many academic projects partly because it
    is robust, well documented, easy-to-use, and can flexibly
    target a range of architectures.

    VPR takes, as input, a description of an FPGA architecture along
    with a technology-mapped user circuit. It then performs packing,
    placement, and routing to map the circuit onto the FPGA. The output
    of VPR includes the FPGA configuration needed to implement the circuit
    and statistics about the final mapped design (eg. critical path delay,
    area, etc).

    Source code:
    * https://github.com/verilog-to-routing/vtr-verilog-to-routing

    Documentation:
    * https://docs.verilogtorouting.org/en/latest

    '''

    chip = siliconcompiler.Chip()
    setup_tool(chip,'apr','<index>')
    return chip

################################
# Setup Tool (pre executable)
################################
def setup_tool(chip, step, index):

     tool = 'vpr'
     refdir = 'siliconcompiler/tools/vpr'

     chip.set('eda', tool, step, index, 'threads', '4')
     chip.set('eda', tool, step, index, 'vendor', 'vpr')
     chip.set('eda', tool, step, index, 'exe', 'vpr')
     chip.set('eda', tool, step, index, 'version', '0.0')

     topmodule = chip.get('design')
     blif = "inputs/" + topmodule + ".blif"

     options = []
     for arch in chip.get('fpga','arch'):
          options.append(arch)

     options.append(blif)

     chip.add('eda', tool, step, index, 'option', 'cmdline', options)

################################
# Post_process (post executable)
################################

def post_process(chip, step ):
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
    setup_tool(chip, step='apr', index='0')
    # write out results
    chip.writecfg(output)
