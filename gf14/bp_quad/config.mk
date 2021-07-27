export DESIGN_NICKNAME = bp_quad
export DESIGN_NAME = bsg_chip
export PLATFORM    = gf14

export VERILOG_FILES = $(PLATFORM_DIR)/bp/bsg_ac_black_parrot_quad_core_v0/bsg_chip.sv2v.v \
                       $(PLATFORM_DIR)/bp/IN12LP_GPIO18_13M9S30P.blackbox.v

# export CACHED_NETLIST    = $(PLATFORM_DIR)/bp/bsg_ac_black_parrot_quad_core_v0/dc/results/bsg_chip.mapped.flat.v
export CACHED_NETLIST    = $(PLATFORM_DIR)/bp/bsg_ac_black_parrot_quad_core_v0/yosys/synth.v

export SDC_FILE      = $(PLATFORM_DIR)/bp/bsg_ac_black_parrot_quad_core_v0/bsg_chip.elab.v.sdc

export ADDITIONAL_LEFS = $(PLATFORM_DIR)/bp/lef/gf14_1r1w_d32_w64_m1.lef \
                         $(PLATFORM_DIR)/bp/lef/gf14_1rw_d128_w116_m2_bit.lef \
                         $(PLATFORM_DIR)/bp/lef/gf14_1rw_d256_w48_m2.lef \
                         $(PLATFORM_DIR)/bp/lef/gf14_1rw_d512_w64_m2_byte.lef \
                         $(PLATFORM_DIR)/bp/lef/gf14_1rw_d64_w124_m2_bit.lef \
                         $(PLATFORM_DIR)/bp/lef/gf14_1rw_d64_w62_m2_bit.lef \
                         $(PLATFORM_DIR)/bp/lef/IN12LP_GPIO18_13M9S30P.lef

export ADDITIONAL_LIBS = $(PLATFORM_DIR)/bp/lib/gf14_1r1w_d32_w64_m1_ffpg_sigcmin_0p88v_0p88v_m40c.lib \
                         $(PLATFORM_DIR)/bp/lib/gf14_1rw_d128_w116_m2_bit_ffpg_sigcmin_0p88v_0p88v_m40c.lib \
                         $(PLATFORM_DIR)/bp/lib/gf14_1rw_d256_w48_m2_ffpg_sigcmin_0p88v_0p88v_m40c.lib \
                         $(PLATFORM_DIR)/bp/lib/gf14_1rw_d512_w64_m2_byte_ffpg_sigcmin_0p88v_0p88v_m40c.lib \
                         $(PLATFORM_DIR)/bp/lib/gf14_1rw_d64_w124_m2_bit_ffpg_sigcmin_0p88v_0p88v_m40c.lib \
                         $(PLATFORM_DIR)/bp/lib/gf14_1rw_d64_w62_m2_bit_ffpg_sigcmin_0p88v_0p88v_m40c.lib \
                         $(PLATFORM_DIR)/bp/lib/IN12LP_GPIO18_13M9S30P_TT_0P8_1P8_25.lib

export ADDITIONAL_GDS  = $(PLATFORM_DIR)/bp/gds/gf14_1r1w_d32_w64_m1.gds2 \
                         $(PLATFORM_DIR)/bp/gds/gf14_1rw_d128_w116_m2_bit.gds2 \
                         $(PLATFORM_DIR)/bp/gds/gf14_1rw_d256_w48_m2.gds2 \
                         $(PLATFORM_DIR)/bp/gds/gf14_1rw_d512_w64_m2_byte.gds2 \
                         $(PLATFORM_DIR)/bp/gds/gf14_1rw_d64_w124_m2_bit.gds2 \
                         $(PLATFORM_DIR)/bp/gds/gf14_1rw_d64_w62_m2_bit.gds2 \
                         $(PLATFORM_DIR)/bp/gds/IN12LP_GPIO18_13M9S30P.gds


export FOOTPRINT    = $(PLATFORM_DIR)/bp/bsg_black_parrot.package.strategy
export SIG_MAP_FILE = $(PLATFORM_DIR)/bp/soc_bsg_black_parrot.sigmap

# These values must be multiples of placement site
# export DIE_AREA    =
# export CORE_AREA   =

export ABC_CLOCK_PERIOD_IN_PS = 1250
