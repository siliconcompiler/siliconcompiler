export DESIGN_NAME ?= SPECIFY_DESIGN_NAME
export PLATFORM    = nangate45

export VERILOG_FILES = ./designs/src/harness/*.v
export SDC_FILE      = ./designs/src/harness/design.sdc

export MERGED_LEF = $(PLATFORM_DIR)/NangateOpenCellLibrary.mod.lef
export LIB_FILES  = $(PLATFORM_DIR)/NangateOpenCellLibrary_typical.lib
export GDS_FILES  = $(sort $(wildcard $(PLATFORM_DIR)/gds/*))

# Automatically pick a reasonable area and utilization

# Core utilization in %
export CORE_UTILIZATION = 10.0
# Core height / core width
export CORE_ASPECT_RATIO = 1.0
# Core margin in um
export CORE_MARGIN = 2.0

# Start with 250MHz for nangate45, relatively conservative
export CLOCK_PERIOD = 4
export CLOCK_PORT   = clock
