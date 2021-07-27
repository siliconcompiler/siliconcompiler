export DESIGN_NAME = swerv_wrapper
export PLATFORM    = gf14

export VERILOG_FILES = ./designs/src/swerv/swerv_wrapper.sv2v.v \
                       ./designs/$(PLATFORM)/$(DESIGN_NAME)/macros.v
export SDC_FILE      = ./designs/$(PLATFORM)/$(DESIGN_NAME)/constraint.sdc

export WRAP_LEFS      = $(PLATFORM_DIR)/lef/gf14_1rf_lg11_w40_all.lef \
                        $(PLATFORM_DIR)/lef/gf14_1rf_lg6_w22_all.lef \
                        $(PLATFORM_DIR)/lef/gf14_1rf_lg8_w34_all.lef

export WRAP_LIBS      = $(PLATFORM_DIR)/lib/gf14_1rf_lg11_w40_all_ffpg_sigcmin_0p88v_0p88v_m40c.lib \
                        $(PLATFORM_DIR)/lib/gf14_1rf_lg6_w22_all_ffpg_sigcmin_0p88v_0p88v_m40c.lib \
                        $(PLATFORM_DIR)/lib/gf14_1rf_lg8_w34_all_ffpg_sigcmin_0p88v_0p88v_m40c.lib

export ADDITIONAL_GDS = $(PLATFORM_DIR)/gds/gf14_1rf_lg11_w40_all.gds2 \
                        $(PLATFORM_DIR)/gds/gf14_1rf_lg6_w22_all.gds2 \
                        $(PLATFORM_DIR)/gds/gf14_1rf_lg8_w34_all.gds2

# These values must be multiples of placement site
export DIE_AREA    = 0 0 970.2 760.896
export CORE_AREA   = 9.996 20.16 960.036 749.952

export PLACE_DENSITY = 0.25
