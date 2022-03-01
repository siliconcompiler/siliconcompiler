
set multiplier 1
if { [info exists ::env(4X)] } {
  set multiplier 4
}

make_tracks Pad -x_offset [expr 0.116 * $multiplier] -x_pitch [expr 0.08  * $multiplier] -y_offset [expr 0.116 * $multiplier] -y_pitch [expr 0.08 * $multiplier]
make_tracks M9  -x_offset [expr 0.116 * $multiplier] -x_pitch [expr 0.08  * $multiplier] -y_offset [expr 0.116 * $multiplier] -y_pitch [expr 0.08 * $multiplier]
make_tracks M8  -x_offset [expr 0.116 * $multiplier] -x_pitch [expr 0.08  * $multiplier] -y_offset [expr 0.116 * $multiplier] -y_pitch [expr 0.08 * $multiplier]
make_tracks M7  -x_offset [expr 0.016 * $multiplier] -x_pitch [expr 0.064 * $multiplier] -y_offset [expr 0.016 * $multiplier] -y_pitch [expr 0.064 * $multiplier]
make_tracks M6  -x_offset [expr 0.012 * $multiplier] -x_pitch [expr 0.048 * $multiplier] -y_offset [expr 0.016 * $multiplier] -y_pitch [expr 0.064 * $multiplier]
make_tracks M5  -x_offset [expr 0.012 * $multiplier] -x_pitch [expr 0.048 * $multiplier] -y_offset [expr 0.012 * $multiplier] -y_pitch [expr 0.048 * $multiplier]
make_tracks M4  -x_offset [expr 0.009 * $multiplier] -x_pitch [expr 0.036 * $multiplier] -y_offset [expr 0.012 * $multiplier] -y_pitch [expr 0.048 * $multiplier]
make_tracks M3  -x_offset [expr 0.009 * $multiplier] -x_pitch [expr 0.036 * $multiplier] -y_offset [expr 0.009 * $multiplier] -y_pitch [expr 0.036 * $multiplier]

make_tracks M2  -x_offset [expr 0.009 * $multiplier] -x_pitch [expr 0.036 * $multiplier] -y_offset [expr (0.045 - 0.000) * $multiplier] -y_pitch [expr 0.270 * $multiplier]
make_tracks M2  -x_offset [expr 0.009 * $multiplier] -x_pitch [expr 0.036 * $multiplier] -y_offset [expr (0.081 - 0.000) * $multiplier] -y_pitch [expr 0.270 * $multiplier]
make_tracks M2  -x_offset [expr 0.009 * $multiplier] -x_pitch [expr 0.036 * $multiplier] -y_offset [expr (0.117 - 0.000) * $multiplier] -y_pitch [expr 0.270 * $multiplier]
make_tracks M2  -x_offset [expr 0.009 * $multiplier] -x_pitch [expr 0.036 * $multiplier] -y_offset [expr (0.153 - 0.000) * $multiplier] -y_pitch [expr 0.270 * $multiplier]
make_tracks M2  -x_offset [expr 0.009 * $multiplier] -x_pitch [expr 0.036 * $multiplier] -y_offset [expr (0.189 - 0.000) * $multiplier] -y_pitch [expr 0.270 * $multiplier]
make_tracks M2  -x_offset [expr 0.009 * $multiplier] -x_pitch [expr 0.036 * $multiplier] -y_offset [expr (0.225 - 0.000) * $multiplier] -y_pitch [expr 0.270 * $multiplier]
make_tracks M2  -x_offset [expr 0.009 * $multiplier] -x_pitch [expr 0.036 * $multiplier] -y_offset [expr (0.270 - 0.000) * $multiplier] -y_pitch [expr 0.270 * $multiplier]

make_tracks M1  -x_offset [expr 0.009 * $multiplier] -x_pitch [expr 0.036 * $multiplier] -y_offset [expr 0.009 * $multiplier] -y_pitch [expr 0.036 * $multiplier]
