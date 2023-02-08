# Adopted from: https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/9895e23b5d4abd4610f8d55ccf8f5173e770375e/flow/platforms/nangate45/setRC.tcl

# Liberty units are fF,kOhm
set_layer_rc {{ corner }} -layer metal1 -resistance 5.4286e-03 -capacitance 7.41819E-02
set_layer_rc {{ corner }} -layer metal2 -resistance 3.5714e-03 -capacitance 6.74606E-02
set_layer_rc {{ corner }} -layer metal3 -resistance 3.5714e-03 -capacitance 8.88758E-02
set_layer_rc {{ corner }} -layer metal4 -resistance 1.5000e-03 -capacitance 1.07121E-01
set_layer_rc {{ corner }} -layer metal5 -resistance 1.5000e-03 -capacitance 1.08964E-01
set_layer_rc {{ corner }} -layer metal6 -resistance 1.5000e-03 -capacitance 1.02044E-01
set_layer_rc {{ corner }} -layer metal7 -resistance 1.8750e-04 -capacitance 1.10436E-01
set_layer_rc {{ corner }} -layer metal8 -resistance 1.8750e-04 -capacitance 9.69714E-02
# No calibration data available for metal9 and metal10
set_layer_rc {{ corner }} -layer metal9 -resistance 3.7500e-05 -capacitance 3.6864e-02
set_layer_rc {{ corner }} -layer metal10 -resistance 3.7500e-05 -capacitance 2.8042e-02
