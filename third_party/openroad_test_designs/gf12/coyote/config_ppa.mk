include $(dir $(DESIGN_CONFIG))/config.mk

export FLOW_VARIANT = ppa

export CELL_PAD_IN_SITES_GLOBAL_PLACEMENT = 2
export CELL_PAD_IN_SITES_DETAIL_PLACEMENT = 2

export GLOBAL_PLACEMENT_ARGS = -timing_driven

export FASTROUTE_TCL = $(PLATFORM_DIR)/fastroute_ppa.tcl

