export DESIGN_NICKNAME = ibex
export DESIGN_NAME = ibex_core
export PLATFORM    = tsmc65lp

export VERILOG_FILES = ./designs/src/$(DESIGN_NICKNAME)/ibex_alu.v \
                       ./designs/src/$(DESIGN_NICKNAME)/ibex_branch_predict.v \
                       ./designs/src/$(DESIGN_NICKNAME)/ibex_compressed_decoder.v \
                       ./designs/src/$(DESIGN_NICKNAME)/ibex_controller.v \
                       ./designs/src/$(DESIGN_NICKNAME)/ibex_core.v \
                       ./designs/src/$(DESIGN_NICKNAME)/ibex_counter.v \
                       ./designs/src/$(DESIGN_NICKNAME)/ibex_cs_registers.v \
                       ./designs/src/$(DESIGN_NICKNAME)/ibex_csr.v \
                       ./designs/src/$(DESIGN_NICKNAME)/ibex_decoder.v \
                       ./designs/src/$(DESIGN_NICKNAME)/ibex_dummy_instr.v \
                       ./designs/src/$(DESIGN_NICKNAME)/ibex_ex_block.v \
                       ./designs/src/$(DESIGN_NICKNAME)/ibex_fetch_fifo.v \
                       ./designs/src/$(DESIGN_NICKNAME)/ibex_icache.v \
                       ./designs/src/$(DESIGN_NICKNAME)/ibex_id_stage.v \
                       ./designs/src/$(DESIGN_NICKNAME)/ibex_if_stage.v \
                       ./designs/src/$(DESIGN_NICKNAME)/ibex_load_store_unit.v \
                       ./designs/src/$(DESIGN_NICKNAME)/ibex_multdiv_fast.v \
                       ./designs/src/$(DESIGN_NICKNAME)/ibex_multdiv_slow.v \
                       ./designs/src/$(DESIGN_NICKNAME)/ibex_pmp.v \
                       ./designs/src/$(DESIGN_NICKNAME)/ibex_prefetch_buffer.v \
                       ./designs/src/$(DESIGN_NICKNAME)/ibex_register_file_ff.v \
                       ./designs/src/$(DESIGN_NICKNAME)/ibex_register_file_fpga.v \
                       ./designs/src/$(DESIGN_NICKNAME)/ibex_register_file_latch.v \
                       ./designs/src/$(DESIGN_NICKNAME)/ibex_wb_stage.v \
                       ./designs/src/$(DESIGN_NICKNAME)/prim_badbit_ram_1p.v \
                       ./designs/src/$(DESIGN_NICKNAME)/prim_clock_gating.v \
                       ./designs/src/$(DESIGN_NICKNAME)/prim_generic_clock_gating.v \
                       ./designs/src/$(DESIGN_NICKNAME)/prim_generic_ram_1p.v \
                       ./designs/src/$(DESIGN_NICKNAME)/prim_lfsr.v \
                       ./designs/src/$(DESIGN_NICKNAME)/prim_ram_1p.v \
                       ./designs/src/$(DESIGN_NICKNAME)/prim_secded_28_22_dec.v \
                       ./designs/src/$(DESIGN_NICKNAME)/prim_secded_28_22_enc.v \
                       ./designs/src/$(DESIGN_NICKNAME)/prim_secded_39_32_dec.v \
                       ./designs/src/$(DESIGN_NICKNAME)/prim_secded_39_32_enc.v \
                       ./designs/src/$(DESIGN_NICKNAME)/prim_secded_72_64_dec.v \
                       ./designs/src/$(DESIGN_NICKNAME)/prim_secded_72_64_enc.v \
                       ./designs/src/$(DESIGN_NICKNAME)/prim_xilinx_clock_gating.v



export SDC_FILE      = ./designs/$(PLATFORM)/$(DESIGN_NICKNAME)/constraint.sdc

export CORE_UTILIZATION = 40 
export CORE_ASPECT_RATIO = 1
export CORE_MARGIN = 5

export PLACE_DENSITY = 0.70
