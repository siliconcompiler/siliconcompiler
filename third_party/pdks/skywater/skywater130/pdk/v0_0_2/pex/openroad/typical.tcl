# Adopted from: https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/9895e23b5d4abd4610f8d55ccf8f5173e770375e/flow/platforms/sky130hd/setRC.tcl

# correlateRC.py gcd,ibex,aes,jpeg,chameleon,riscv32i,chameleon_hier
# cap units pf/um
set_layer_rc {{ corner }} -layer li1 -capacitance 1.499e-04 -resistance 7.176e-02
set_layer_rc {{ corner }} -layer met1 -capacitance 1.72375E-04 -resistance 8.929e-04
set_layer_rc {{ corner }} -layer met2 -capacitance 1.36233E-04 -resistance 8.929e-04
set_layer_rc {{ corner }} -layer met3 -capacitance 2.14962E-04 -resistance 1.567e-04
set_layer_rc {{ corner }} -layer met4 -capacitance 1.48128E-04 -resistance 1.567e-04
set_layer_rc {{ corner }} -layer met5 -capacitance 1.54087E-04 -resistance 1.781e-05
# end correlate

set_layer_rc {{ corner }} -via mcon -resistance 9.249146E-3
set_layer_rc {{ corner }} -via via -resistance 4.5E-3
set_layer_rc {{ corner }} -via via2 -resistance 3.368786E-3
set_layer_rc {{ corner }} -via via3 -resistance 0.376635E-3
set_layer_rc {{ corner }} -via via4 -resistance 0.00580E-3
