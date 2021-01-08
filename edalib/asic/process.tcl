
# Read tech lef
read_lef $SC_TECHFILE

#hack!, fix later
#fix should be to auto-generate this file from parameters in tcl file 
file copy -force /home/aolofsson/work/zeroasic/siliconcompiler/pdklib/virtual/nangate45/r1p0/pnr/tracks.info sc_tracks.txt

