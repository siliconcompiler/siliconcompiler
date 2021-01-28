# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
#
# This example shows how one could map from legacy names to
# the siliconcompiler names. The example specifically
# translates from the openroad make format.
# https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts

import siliconcompiler as sc

# Create instance of Chip class
chip = sc.Chip()

# Design values
all_stages = chip.get('sc_stages')
for stage in all_stages:

    # design
    chip.set('sc_tool', stage, 'keymap', "sc_design      DESIGN_NAME")
    chip.set('sc_tool', stage, 'keymap', "sc_nickname    DESIGN_NICKNAME")
    chip.set('sc_tool', stage, 'keymap', "sc_source      VERILOG_FILES")
    chip.set('sc_tool', stage, 'keymap', "sc_constraint  SDC_FILE")
    chip.set('sc_tool', stage, 'keymap', "sc_diesize     DIE_AREA")
    chip.set('sc_tool', stage, 'keymap', "sc_coresize    CORE_AREA")
    chip.set('sc_tool', stage, 'keymap', "sc_process     PLATFORM")
    # platform
    chip.set('sc_tool', stage, 'keymap', "sc_techfile    TECH_LEF")
    chip.set('sc_tool', stage, 'keymap', "sc_node        PROCESS")
    chip.set('sc_tool', stage, 'keymap', "sc_maxfanout   MAX_FANOUT")
    chip.set('sc_tool', stage, 'keymap', "sc_hold        HOLD_BUF_CELL")
    chip.set('sc_tool', stage, 'keymap', "sc_site        PLACE_SITE")
    chip.set('sc_tool', stage, 'keymap', "sc_gds         GDS_FILES")
    chip.set('sc_tool', stage, 'keymap', "sc_lef         SC_LEF")
    chip.set('sc_tool', stage, 'keymap', "sc_minlayer    MIN_ROUTING_LAYER")
    chip.set('sc_tool', stage, 'keymap', "sc_maxlayer    MAX_ROUTING_LAYER")
    
# Print out new merged config to a file
chip.writecfg("rename.json") 

# Print out mapped tcl
chip.writetcl("place", "place.tcl") 
