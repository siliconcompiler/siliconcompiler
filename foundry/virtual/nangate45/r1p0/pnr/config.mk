# Process node
export PROCESS = 45

# Set the TIEHI/TIELO cells
# These are used in yosys synthesis to avoid logical 1/0's in the netlist
export TIEHI_CELL_AND_PORT = LOGIC1_X1 Z
export TIELO_CELL_AND_PORT = LOGIC0_X1 Z

# Used in synthesis
export MIN_BUF_CELL_AND_PORTS = BUF_X1 A Z

# Resizer hold buffer
export HOLD_BUF_CELL = BUF_X1

# Used in synthesis
export MAX_FANOUT = 100

# Blackbox verilog file
# List all standard cells and cells yosys should treat as blackboxes here
export BLACKBOX_V_FILE = ./platforms/$(PLATFORM)/NangateOpenCellLibrary.blackbox.v
export BLACKBOX_LVS_FILE = ./platforms/$(PLATFORM)/NangateOpenCellLibrary.blackbox.lvs.v

# Yosys mapping files
export LATCH_MAP_FILE = ./platforms/$(PLATFORM)/cells_latch.v
export CLKGATE_MAP_FILE = ./platforms/$(PLATFORM)/cells_clkgate.v
export BLACKBOX_MAP_TCL = ./platforms/$(PLATFORM)/blackbox_map.tcl

# Placement site for core cells
# This can be found in the technology lef
export PLACE_SITE = FreePDK45_38x28_10R_NP_162NW_34O

# Track information for generating DEF tracks
export TRACKS_INFO_FILE = ./platforms/$(PLATFORM)/tracks.info

export IP_GLOBAL_CFG = ./platforms/$(PLATFORM)/IP_global.cfg

export TECH_LEF = ./platforms/$(PLATFORM)/lef/NangateOpenCellLibrary.tech.lef
export SC_LEF = ./platforms/$(PLATFORM)/lef/NangateOpenCellLibrary.macro.mod.lef

export LIB_FILES = ./platforms/$(PLATFORM)/lib/NangateOpenCellLibrary_typical.lib \
                     $(ADDITIONAL_LIBS)
export GDS_FILES = $(sort $(wildcard ./platforms/$(PLATFORM)/gds/*.gds)) \
                     $(ADDITIONAL_GDS)

# Cell padding in SITE widths to ease rout-ability.  Applied to both sides
export CELL_PAD_IN_SITES_GLOBAL_PLACEMENT = 2
export CELL_PAD_IN_SITES_DETAIL_PLACEMENT = 1

# Endcap and Welltie cells
export TAPCELL_TCL = ./platforms/$(PLATFORM)/tapcell.tcl

# TritonCTS options
export CTS_BUF_CELL   = BUF_X4
export CTS_TECH_DIR   = ./platforms/$(PLATFORM)/tritonCTS
export CTS_MAX_SLEW   = .198e-9
export CTS_MAX_CAP    = .242e-12

# FastRoute options
export MIN_ROUTING_LAYER = 2
export MAX_ROUTING_LAYER = 10

# IO Pin fix margin
export IO_PIN_MARGIN = 70

# Layer to use for parasitics estimations
export WIRE_RC_LAYER = metal3

# resizer repair_long_wires -max_length
export MAX_WIRE_LENGTH = 1000

# KLayout technology file
export KLAYOUT_TECH_FILE = ./platforms/$(PLATFORM)/FreePDK45.lyt

# KLayout DRC ruledeck
export KLAYOUT_DRC_FILE = ./platforms/$(PLATFORM)/drc/FreePDK45.lydrc

# KLayout LVS ruledeck
export KLAYOUT_LVS_FILE = ./platforms/$(PLATFORM)/lvs/FreePDK45.lylvs

export CDL_FILE = ./platforms/$(PLATFORM)/cdl/NangateOpenCellLibrary.cdl

# Dont use cells to ease congestion
# Specify at least one filler cell if none
export DONT_USE_CELLS = FILLCELL_X1 AOI211_X1 OAI211_X1

# Fill cells used in fill cell insertion
export FILL_CELLS = FILLCELL_X1 FILLCELL_X2 FILLCELL_X4 FILLCELL_X8 FILLCELL_X16 FILLCELL_X32

# Define default PDN config
export PDN_CFG ?= ./platforms/$(PLATFORM)/pdn.cfg

# Template definition for power grid analysis
export TEMPLATE_PGA_CFG ?= ./platforms/nangate45/template_pga.cfg

export PLACE_DENSITY ?= 0.30

# IO Placer pin layers
export IO_PLACER_H = 3
export IO_PLACER_V = 2

# Set yosys-abc clock period to first "-period" found in sdc file
export ABC_CLOCK_PERIOD_IN_PS ?= $(shell grep -E -o -m 1 "\-period\s+\S+" $(SDC_FILE) | awk '{print $$2*1000}')
export ABC_DRIVER_CELL = BUF_X1
# BUF_X1, pin (A) = 0.974659. Arbitrarily multiply by 4
export ABC_LOAD_IN_FF = 3.898
