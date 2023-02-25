import os
import siliconcompiler

def setup(chip):
    '''
    "Self-test" target which builds a small 8-bit counter design as an ASIC,
    targeting the Skywater130 PDK.

    This target is not intended for general-purpose use.
    It is intended to quickly verify that SiliconCompiler is installed and configured correctly.
    '''

    # Load the Sky130 PDK/standard cell library target.
    chip.load_target('skywater130_demo')

    # Create temporary source files. (Examples are not currently included in the wheel build)
    build_dir = chip.get('option', 'builddir')
    os.makedirs(build_dir, exist_ok=True)
    with open(f'{build_dir}/heartbeat.v', 'w') as hdl:
        hdl.write('''\
module heartbeat #(parameter N = 8)
   (input clk, input nreset, output reg out);
   reg [N-1:0] counter_reg;
   always @ (posedge clk or negedge nreset)
     if(!nreset) begin
        counter_reg <= 'b0;
        out <= 1'b0;
     end else begin
        counter_reg[N-1:0] <= counter_reg[N-1:0] + 1'b1;
        out <= (counter_reg[N-1:0]=={(N){1'b1}});
     end
endmodule''')
    with open(f'{build_dir}/heartbeat.sdc', 'w') as constraints:
        constraints.write('create_clock -name clk -period 10 [get_ports {clk}]')

    # Set design name and source files.
    chip.set('design', 'heartbeat')
    chip.input(f'{build_dir}/heartbeat.v')
    chip.input(f'{build_dir}/heartbeat.sdc')

#########################
if __name__ == "__main__":
    target = siliconcompiler.Chip('<target>')
    setup(target)
    target.write_manifest('asic_demo.json')
