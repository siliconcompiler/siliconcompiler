# Bambu names the clock port of the RTL it generates "clock", so the constraint
# has to be attached to that port. The period here is what the HLS scheduler
# targets, and the same file then constrains synthesis and place-and-route.
create_clock [get_ports clock] -name core_clock -period 5

set_input_delay 1.0 -clock core_clock [all_inputs]
set_output_delay 1.0 -clock core_clock [all_outputs]
