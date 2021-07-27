undefine BLOCKS
undefine ADDITIONAL_LEFS
undefine ADDITIONAL_GDS
undefine DONT_USE_SC_LIB

export TOP_NICKNAME = chameleon_hier
export TOP_DIR = ./designs/$(PLATFORM)/${TOP_NICKNAME}

export DESIGN_NAME = ibex_wrapper
export DESIGN_NICKNAME = ${TOP_NICKNAME}_${DESIGN_NAME}
export PLATFORM    = sky130hd
export RTL_DIR  = ./designs/src/${TOP_NICKNAME}/rtl

export VERILOG_FILES = \
                         ${RTL_DIR}/ibex/ibex_core.v\
                         ${RTL_DIR}/ibex/ibex_pmp.v\
                         ${RTL_DIR}/ibex/ibex_controller.v\
                         ${RTL_DIR}/ibex/ibex_decoder.v\
                         ${RTL_DIR}/ibex/ibex_id_stage.v\
                         ${RTL_DIR}/ibex/ibex_wb_stage.v\
                         ${RTL_DIR}/ibex/ibex_ex_block.v\
                         ${RTL_DIR}/ibex/ibex_branch_predict.v\
                         ${RTL_DIR}/ibex/ibex_icache.v\
                         ${RTL_DIR}/ibex/ibex_compressed_decoder.v\
                         ${RTL_DIR}/ibex/ibex_prefetch_buffer.v\
                         ${RTL_DIR}/ibex/ibex_if_stage.v\
                         ${RTL_DIR}/ibex/ibex_register_file_latch.v\
                         ${RTL_DIR}/ibex/ibex_cs_registers.v\
                         ${RTL_DIR}/ibex/ibex_csr.v\
                         ${RTL_DIR}/ibex/ibex_register_file_ff.v\
                         ${RTL_DIR}/ibex/ibex_load_store_unit.v\
                         ${RTL_DIR}/ibex/ibex_alu.v\
                         ${RTL_DIR}/ibex/ibex_counter.v\
                         ${RTL_DIR}/ibex/ibex_dummy_instr.v\
                         ${RTL_DIR}/ibex/ibex_multdiv_fast.v\
                         ${RTL_DIR}/ibex/ibex_multdiv_slow.v\
                         ${RTL_DIR}/ibex/prim_clock_gating.v\
                         ${RTL_DIR}/ibex/ibex_fetch_fifo.v\
                         ${RTL_DIR}/ibex/ibex_wrapper.v

export SDC_FILE          = ${TOP_DIR}/${DESIGN_NAME}/constraint.sdc

export PDN_CFG = ${TOP_DIR}/${DESIGN_NAME}/pdn.cfg

export ABC_CLOCK_PERIOD_IN_PS = 10000
export ABC_DRIVER_CELL = sky130_fd_sc_hd__buf_1
export ABC_LOAD_IN_FF = 3



# These values must be multiples of placement site
export DIE_AREA    = 0 0 900 1200
export CORE_AREA    = 0.46 2.720 899.54 1197.28

export MIN_ROUTING_LAYER 2
export MAX_ROUTING_LAYER 5


# IR drop estimation supply net name to be analyzed and supply voltage variable
# For multiple nets: PWR_NETS_VOLTAGES  = "VDD1 1.8 VDD2 1.2"
export PWR_NETS_VOLTAGES  = "VDD 1.8"
export GND_NETS_VOLTAGES  = "VSS 0.0"
