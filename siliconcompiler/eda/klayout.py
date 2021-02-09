
import pya
import re
import copy
import sys

def setup_klayout(chip, root):

     refdir = root + '/klayout'
     
     for stage in (['export', 'gdsview']):
          chip.add('sc_tool', stage, 'np', '4')
          chip.add('sc_tool', stage, 'format', 'tcl')
          chip.add('sc_tool', stage, 'copy', 'False')
          chip.add('sc_tool', stage, 'vendor', 'klayout')
          chip.add('sc_tool', stage, 'exe', 'klayout') 
          chip.add('sc_tool', stage, 'refdir', refdir)
          if stage == 'gdsview':               
               chip.add('sc_tool', stage, 'opt', '-nn')
          elif stage == 'export':               
               chip.add('sc_tool', stage, 'opt', '-rm')   

