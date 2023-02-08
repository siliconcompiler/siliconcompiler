# Adopted from: https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/9895e23b5d4abd4610f8d55ccf8f5173e770375e/flow/platforms/asap7/setRC.tcl

# Liberty units are fF,kOhm
set_layer_rc {{ corner }} -layer M1 -capacitance 1.1368e-01 -resistance 1.3889e-01
set_layer_rc {{ corner }} -layer M2 -capacitance 1.3426e-01 -resistance 2.4222e-02
set_layer_rc {{ corner }} -layer M3 -capacitance 1.2918e-01 -resistance 2.4222e-02
set_layer_rc {{ corner }} -layer M4 -capacitance 1.1396e-01 -resistance 1.6778e-02
set_layer_rc {{ corner }} -layer M5 -capacitance 1.3323e-01 -resistance 1.4677e-02
set_layer_rc {{ corner }} -layer M6 -capacitance 1.1575e-01 -resistance 1.0371e-02
set_layer_rc {{ corner }} -layer M7 -capacitance 1.3293e-01 -resistance 9.6720e-03
set_layer_rc {{ corner }} -layer M8 -capacitance 1.1822e-01 -resistance 7.4310e-03
set_layer_rc {{ corner }} -layer M9 -capacitance 1.3497e-01 -resistance 6.8740e-03

set_layer_rc {{ corner }} -via V1 -resistance 1.72E-02
set_layer_rc {{ corner }} -via V2 -resistance 1.72E-02
set_layer_rc {{ corner }} -via V3 -resistance 1.72E-02
set_layer_rc {{ corner }} -via V4 -resistance 1.18E-02
set_layer_rc {{ corner }} -via V5 -resistance 1.18E-02
set_layer_rc {{ corner }} -via V6 -resistance 8.20E-03
set_layer_rc {{ corner }} -via V7 -resistance 8.20E-03
set_layer_rc {{ corner }} -via V8 -resistance 6.30E-03
