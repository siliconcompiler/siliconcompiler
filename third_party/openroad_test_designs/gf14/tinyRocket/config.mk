export DESIGN_NICKNAME = tinyRocket
export DESIGN_NAME = RocketTile
export PLATFORM    = gf14

export VERILOG_FILES  = ./designs/src/$(DESIGN_NICKNAME)/AsyncResetReg.v \
                        ./designs/src/$(DESIGN_NICKNAME)/ClockDivider2.v \
                        ./designs/src/$(DESIGN_NICKNAME)/ClockDivider3.v \
                        ./designs/src/$(DESIGN_NICKNAME)/plusarg_reader.v \
                        ./designs/src/$(DESIGN_NICKNAME)/freechips.rocketchip.system.TinyConfig.v \
                        ./designs/$(PLATFORM)/$(DESIGN_NICKNAME)/macros.v

export SDC_FILE       = ./designs/$(PLATFORM)/$(DESIGN_NICKNAME)/constraint.sdc

export WRAP_LEFS      = $(PLATFORM_DIR)/lef/gf14_1rf_lg6_w32_all.lef \
                        $(PLATFORM_DIR)/lef/gf14_1rf_lg6_w32_byte.lef \
                        $(PLATFORM_DIR)/lef/gf14_2rf_lg10_w32_bit.lef

export WRAP_LIBS      = $(PLATFORM_DIR)/lib/gf14_1rf_lg6_w32_all_ffpg_sigcmin_0p88v_0p88v_m40c.lib \
                        $(PLATFORM_DIR)/lib/gf14_1rf_lg6_w32_byte_ffpg_sigcmin_0p88v_0p88v_m40c.lib \
                        $(PLATFORM_DIR)/lib/gf14_2rf_lg10_w32_bit_ffpg_sigcmin_0p88v_0p88v_m40c.lib

export ADDITIONAL_GDS = $(PLATFORM_DIR)/gds/gf14_1rf_lg6_w32_all.gds2 \
                        $(PLATFORM_DIR)/gds/gf14_1rf_lg6_w32_byte.gds2 \
                        $(PLATFORM_DIR)/gds/gf14_2rf_lg10_w32_bit.gds2 \

# These values must be multiples of placement site
export DIE_AREA    = 0 0 400.008 399.84
export CORE_AREA   = 19.992 20.16 380.016 380.16

export ABC_CLOCK_PERIOD_IN_PS = 1250

export PLACE_DENSITY = 0.20

export MACRO_WRAPPERS = ./designs/$(PLATFORM)/$(DESIGN_NICKNAME)/wrappers.tcl

export PDN_CFG ?= $(PLATFORM_DIR)/pdn_grid_strategy_13m_9T.top.cfg

# TODO: replace this with max(CHANNEL_WIDTH_[HV]) from IP_global.cfg
export MACRO_BLOCKAGE_HALO = 25
