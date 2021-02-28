##NOTE: This is python code that will only work when called by klayout

import pya
import re
import copy
import sys
import siliconcompiler as sc

def gds_export(techfile, design, def_input, gds_libs, gds_output):
     ''' This function converts a DEF to a GDSII database
     
     '''
     
     # Technology Setup
     tech = pya.Technology()        
     tech.load(techfile)
     tech_options = tech.load_layout_options

     # Loading DEF Database
     input_db = pya.Layout()
     input_db.read(def_input, tech_options)

     # Creating a clean cell
     top_cell = input_db.cell(design).cell_index()
     for i in input_db.each_cell():
          if i.cell_index() != top_cell:
               if not i.name.startswith("VIA"):
                    i.clear()

     # Reading in GDS libs
     for filename in gds_libs:
          input_db.read(filename)

     # Creating outputs database
     output_db = pya.Layout()

     # Copying over database unit
     output_db.dbu = input_db.dbu

     # Creating a clean top level cell
     topcell = output_db.create_cell(design)

     # COPY 
     topcell.copy_tree(input_db.cell(design))

     # WRITE GDS
     output_db.write(out_gds)


#Read JSON config file
chip = sc.Chip()
chip.readcfg("sc_setup.json")

techfile = 
design = sc.get('sc_design')
def_input = 'inputs/' + design + ".def"

if (mode=="export"):
    gds_export(techfile, design, def_input, gds_libs, gds_output)

     
