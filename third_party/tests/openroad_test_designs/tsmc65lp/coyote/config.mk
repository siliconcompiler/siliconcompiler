export DESIGN_NICKNAME = coyote
export DESIGN_NAME = bsg_rocket_node_client_rocc
export PLATFORM    = tsmc65lp

export VERILOG_FILES = ./designs/src/$(DESIGN_NICKNAME)/coyote.sv2v.v \
                       ./designs/$(PLATFORM)/$(DESIGN_NICKNAME)/macros.v
export SDC_FILE      = ./designs/$(PLATFORM)/$(DESIGN_NICKNAME)/constraint.sdc

export ADDITIONAL_LEFS = $(PLATFORM_DIR)/lef/tsmc65lp_1rf_lg6_w80_bit.lef \
                         $(PLATFORM_DIR)/lef/tsmc65lp_1rf_lg8_w128_all.lef \
                         $(PLATFORM_DIR)/lef/tsmc65lp_2rf_lg6_w44_bit.lef \
                         $(PLATFORM_DIR)/lef/tsmc65lp_2rf_lg8_w64_bit.lef
export ADDITIONAL_LIBS = $(PLATFORM_DIR)/lib/tsmc65lp_1rf_lg6_w80_bit_ss_1p08v_1p08v_125c.lib \
                         $(PLATFORM_DIR)/lib/tsmc65lp_1rf_lg8_w128_all_ss_1p08v_1p08v_125c.lib \
                         $(PLATFORM_DIR)/lib/tsmc65lp_2rf_lg6_w44_bit_ss_1p08v_1p08v_125c.lib \
                         $(PLATFORM_DIR)/lib/tsmc65lp_2rf_lg8_w64_bit_ss_1p08v_1p08v_125c.lib
export ADDITIONAL_GDS  = $(PLATFORM_DIR)/gds/tsmc65lp_1rf_lg6_w80_bit.gds2 \
                         $(PLATFORM_DIR)/gds/tsmc65lp_1rf_lg8_w128_all.gds2 \
                         $(PLATFORM_DIR)/gds/tsmc65lp_2rf_lg6_w44_bit.gds2 \
                         $(PLATFORM_DIR)/gds/tsmc65lp_2rf_lg8_w64_bit.gds2

# These values must be multiples of placement site
export DIE_AREA = 0 0 3080 3100
export CORE_AREA = 4 4 3076 3096
export MACRO_BLOCKAGE_HALO = 10

export PLACE_DENSITY         ?= 0.45
export REMOVE_BUFFER_TREE     = 1

#export CORE_UTILIZATION = 10
#export CORE_ASPECT_RATIO = 1
#export CORE_MARGIN = 2
