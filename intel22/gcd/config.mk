$(info [INFO-FLOW] GCD Design)
DESIGN_DIR                   := $(realpath $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST)))))
DESIGN_PDK_HOME              := $(realpath $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST)))))

export DESIGN_NAME            = gcd
export DESIGN_NICKNAME        = gcd
export DESIGN                 = gcd

export PLATFORM               = intel22

export VERILOG_FILES          = $(sort $(wildcard $(abspath $(DESIGN_HOME)/src/$(DESIGN))/*.v))
export SDC_FILE               = $(DESIGN_DIR)/constraint.sdc

export CORNER                ?= BC

export LIB_FILES             += $($(CORNER)_LIB_FILES)
export LIB_DIRS              += $($(CORNER)_LIB_DIRS)
export DB_FILES              += $($(CORNER)_DB_FILES)
export DB_DIRS               += $($(CORNER)_DB_DIRS)
export WRAP_LIBS             += $(WRAP_$(CORNER)_LIBS)
export WRAP_LEFS             += $(WRAP_$(CORNER)_LEFS)
export TEMPERATURE            = $($(CORNER)_TEMPERATURE)

export ABC_CLOCK_PERIOD_IN_PS = 400

export DESIGN_POWER           = VDD
export DESIGN_GROUND          = VSS

export PDN_CFG                = $(FOUNDRY_DIR)/openRoad/pdn/grid_strategy-M1-M5-M7.cfg

export PLACE_DENSITY          = 0.35

export DIE_AREA               = 0 0 50 50
export CORE_AREA              = 1.26 1.89 49 49

export DESIGN_DIR DESIGN_PDK_HOME
