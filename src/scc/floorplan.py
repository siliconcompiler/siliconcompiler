# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import math
import logging

#############################
#Snaps value to routing grid
def snap2grid (val, grid):
    return(grid * math.ceil(val/grid))


#####################
#Place a list of pins
#Everything starts in the lower left corer (0,0) and counts up and to the right

def place_pinlist (pinlist, side, block_w, block_h, offset, pinwidth, pindepth, pinhalo, pitch, metal):

    logging.debug('Executing place_pinlist',pinlist, side, block_w, block_h, offset, pinwidth, pindepth, pinhalo, pitch, metal)
    
    if(side=='no'):
        x0    = offset
        y0    = block_h - halo
        x1    = x0 + pinwidth
        y1    = y0 - pindepth + 2 * halo
        xincr = pitch
        yincr = 0.0
    elif (side == 'so'):
        x0    = offset
        y0    = halo
        x1    = x0 + pinwidth
        y1    = y0 + pindepth - 2 * halo
        xincr = pitch
        yincr = 0.0
    elif (side == 'we'):
        x0    = halo
        y0    = offset
        x1    = x0 + pindepth - 2 * halo
        y1    = y0 + pinwidth
        xincr = 0.0 
        yincr = pitch
    elif (side == 'ea'):
        x0    = block_w - halo
        y0    = offset
        x1    = x0 - pindepth + 2 * halo
        y1    = y0 + pinwidth
        xincr = 0.0
        yincr = pitch
    
    #loop through all pins
    for name in pinlist:
        box = [x0,y0,x1,y1]
        place_pin (name, box, metal)
        #Update with new values
        x0 = x0 + xincr
        y0 = y0 + yincr
        x1 = x1 + xincr
        y1 = y1 + yincr


####################
# Place a single pin
def place_pin (name, box, metal):
    logging.debug('Executing place_pin', name, box, metal)

