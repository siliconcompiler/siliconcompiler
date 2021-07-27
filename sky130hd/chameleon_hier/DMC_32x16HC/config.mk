undefine BLOCKS
undefine ADDITIONAL_LEFS
undefine ADDITIONAL_GDS
undefine DONT_USE_SC_LIB

export TOP_NICKNAME = chameleon_hier
export TOP_DIR = ./designs/$(PLATFORM)/${TOP_NICKNAME}

export DESIGN_NAME = DMC_32x16HC
export DESIGN_NICKNAME = ${TOP_NICKNAME}_${DESIGN_NAME}
export PLATFORM    = sky130hd
export RTL_DIR  = ./designs/src/${TOP_NICKNAME}/rtl

export VERILOG_FILES = \
                         ${RTL_DIR}/IPs/DFFRAMBB.v \
                         ${RTL_DIR}/IPs/DMC_32x16HC.v


export SDC_FILE = ${TOP_DIR}/${DESIGN_NAME}/constraint.sdc

export PDN_CFG = ${TOP_DIR}/${DESIGN_NAME}/pdn.cfg

export ABC_CLOCK_PERIOD_IN_PS = 10000
export ABC_DRIVER_CELL = sky130_fd_sc_hd__buf_1
export ABC_LOAD_IN_FF = 3

# These values must be multiples of placement site
export DIE_AREA    = 0 0 600 900
export CORE_AREA    = 0.46 2.720 599.54 897.28

export MIN_ROUTING_LAYER 2
export MAX_ROUTING_LAYER 5

# IR drop estimation supply net name to be analyzed and supply voltage variable
# For multiple nets: PWR_NETS_VOLTAGES  = "VDD1 1.8 VDD2 1.2"
export PWR_NETS_VOLTAGES  = "VDD 1.8"
export GND_NETS_VOLTAGES  = "VSS 0.0"
