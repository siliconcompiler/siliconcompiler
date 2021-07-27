export DESIGN_NICKNAME = chameleon
export DESIGN_NAME     = soc_core
export PLATFORM        = sky130hd

export VERILOG_FILES_BLACKBOX = ./designs/src/$(DESIGN_NICKNAME)/ibex/*.v \
                                ./designs/src/$(DESIGN_NICKNAME)/IPs/DFFRAM_4K.v \
                                ./designs/src/$(DESIGN_NICKNAME)/AHB_sys_0/APB_sys_0/*.v \
                                ./designs/src/$(DESIGN_NICKNAME)/IPs/DMC_32x16HC.v

export VERILOG_FILES = ./designs/src/$(DESIGN_NICKNAME)/acc/AHB_SPM.v \
                       ./designs/src/$(DESIGN_NICKNAME)/IPs/AHBSRAM.v \
                       ./designs/src/$(DESIGN_NICKNAME)/IPs/DFFRAMBB.v \
                       ./designs/src/$(DESIGN_NICKNAME)/IPs/GPIO.v \
                       ./designs/src/$(DESIGN_NICKNAME)/IPs/APB_I2C.v \
                       ./designs/src/$(DESIGN_NICKNAME)/IPs/APB_SPI.v \
                       ./designs/src/$(DESIGN_NICKNAME)/IPs/APB_UART.v \
                       ./designs/src/$(DESIGN_NICKNAME)/IPs/i2c_master.v \
                       ./designs/src/$(DESIGN_NICKNAME)/IPs/PWM32.v \
                       ./designs/src/$(DESIGN_NICKNAME)/IPs/RAM_3Kx32.v \
                       ./designs/src/$(DESIGN_NICKNAME)/IPs/QSPI_XIP_CTRL.v \
                       ./designs/src/$(DESIGN_NICKNAME)/IPs/spi_master.v \
                       ./designs/src/$(DESIGN_NICKNAME)/IPs/TIMER32.v \
                       ./designs/src/$(DESIGN_NICKNAME)/IPs/WDT32.v \
                       ./designs/src/$(DESIGN_NICKNAME)/AHB_sys_0/*.v \
                       ./designs/src/$(DESIGN_NICKNAME)/soc_core.v \
                       $(VERILOG_FILES_BLACKBOX)

export SDC_FILE      = ./designs/$(PLATFORM)/$(DESIGN_NICKNAME)/constraint.sdc

export DIE_AREA   = 0 0 2920 3520
export CORE_AREA  = 20 20 2900 3500

export chameleon_DIR = $(PLATFORM_DIR)/chameleon

export ADDITIONAL_GDS_FILES  = $(chameleon_DIR)/gds/apb_sys_0.gds.gz \
                               $(chameleon_DIR)/gds/DMC_32x16HC.gds.gz \
                               $(chameleon_DIR)/gds/DFFRAM_4K.gds.gz \
                               $(chameleon_DIR)/gds/ibex_wrapper.gds.gz

export ADDITIONAL_LEFS  = $(chameleon_DIR)/lef/apb_sys_0.lef \
                          $(chameleon_DIR)/lef/DFFRAM_4K.lef \
                          $(chameleon_DIR)/lef/DMC_32x16HC.lef \
                          $(chameleon_DIR)/lef/ibex_wrapper.lef

export MACRO_PLACEMENT = $(chameleon_DIR)/chameleon.macro_placment.cfg

export FP_PDN_RAIL_WIDTH = 0.48
export FP_PDN_RAIL_OFFSET = 0

# IR drop estimation supply net name to be analyzed and supply voltage variable
# For multiple nets: PWR_NETS_VOLTAGES  = "VDD1 1.8 VDD2 1.2"
export PWR_NETS_VOLTAGES  = "VDD 1.8"
export GND_NETS_VOLTAGES  = "VSS 0.0"
