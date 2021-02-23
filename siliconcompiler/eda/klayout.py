
import pya
import re
import copy
import sys

def setup_klayout(chip, root):

     refdir = root + '/klayout'
     
     for stage in (['export', 'gdsview']):
          chip.add('tool', stage, 'threads', '4')
          chip.add('tool', stage, 'format', 'tcl')
          chip.add('tool', stage, 'copy', 'False')
          chip.add('tool', stage, 'vendor', 'klayout')
          chip.add('tool', stage, 'exe', 'klayout') 
          chip.add('tool', stage, 'refdir', refdir)
          if stage == 'gdsview':               
               chip.add('tool', stage, 'opt', '-nn')
          elif stage == 'export':               
               chip.add('tool', stage, 'opt', '-rm')   

