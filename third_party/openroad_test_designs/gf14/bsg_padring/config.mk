export DESIGN_NICKNAME = bsg_padring
export DESIGN_NAME = bsg_chip
export PLATFORM    = gf14

export VERILOG_FILES = $(PLATFORM_DIR)/bp/bsg_ac_padring/bsg_chip.sv2v.v \
                       $(PLATFORM_DIR)/bp/IN12LP_GPIO18_13M9S30P.blackbox.v

# export CACHED_NETLIST    = $(PLATFORM_DIR)/bp/bsg_ac_padring/dc/results/bsg_chip.mapped.flat.v
# export CACHED_NETLIST    = $(PLATFORM_DIR)/bp/bsg_ac_padring/yosys/synth.v

export SDC_FILE      = $(PLATFORM_DIR)/bp/bsg_ac_padring/bsg_chip.elab.v.sdc

export ADDITIONAL_LEFS = $(PLATFORM_DIR)/bp/lef/IN12LP_GPIO18_13M9S30P.lef

export ADDITIONAL_LIBS = $(PLATFORM_DIR)/bp/lib/IN12LP_GPIO18_13M9S30P_TT_0P8_1P8_25.lib

export ADDITIONAL_GDS  = $(PLATFORM_DIR)/bp/gds/IN12LP_GPIO18_13M9S30P.gds


export FOOTPRINT    = $(PLATFORM_DIR)/bp/bsg_black_parrot.package.strategy
export SIG_MAP_FILE = $(PLATFORM_DIR)/bp/soc_bsg_black_parrot.sigmap

# These values must be multiples of placement site
# export DIE_AREA    =
# export CORE_AREA   =

export ABC_CLOCK_PERIOD_IN_PS = 1250
