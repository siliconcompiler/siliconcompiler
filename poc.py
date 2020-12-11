#!/usr/bin/python3
import os
import re
import sys
import multiprocessing as mp

class chip:
    def __init__(self, name):
        self.id=name                            #name of object
        self.cfg=cfg                            #
        print("***New***")
    #LAYOUT FLOW
    def setup(self,output):
         print("***Setup***")
    def syn(self,input,output):
         print("***Syn***")
    def place(self,input,output):
         print("***Place***")
    def cts(self,input,output):
         print("***CTS***")     
    def route(self,input,output):
         print("***Route***")
    def cleanup(self,input,output):
         print("***Cleanup***")
    def gdsout(self,input,output):
         print("***Export***")
    #VERIFICATION FLOW
    def leq(self,output):
         print("***Logical Equivalence***")   
    def sta(self,input,output):
         print("***Timing Signoff***")
    def si(self,input,output):
         print("***Signal Integrity***")
    def pi(self,input,output):
         print("***Power Integrity***")     
    def drc(self,input,output):
         print("***DRC***")
    def lvs(self,input,output):
         print("***LVDS***")
    

##########################################################
#End to End Linear Execution flow
##########################################################

globalcfg="test.cfg"
id=0

a = chip(globalcfg,id)

#Should be able to run many route experiments and selet the best one
#Make dynamic, experiments
a.setup("b")
a.syn("cfg1","b","c")
a.place("cfg2","c","d")
a.cts("cfg3","d","e")
a.route("cfg4","e","f")
a.cleanup("cfg5","f","g")
a.export("cfg6","g","h")

##########################################################
#Select from the best (one directory per stage)
##########################################################
a.setup("b")
a.syn("cfg1","setup","syn")
for(i=0;i<10;i++):
    a.place("cfg2","syn","place" + n)
#Check Max, the set d accordingly
a.cts("cfg3","d","e")
a.route("cfg4","e","f")
a.cleanup("cfg5","f","g")
a.export("cfg6","g","h")

##########################################################
#Implicit Fork Join Flow
##########################################################

## Servers, # threads, blocking-nonblocking set by config

wait="wait"
myname="h"

a.leq(myname) ##servers, blocking, # threads
a.sta(myname)
a.si(myname)
a.pi(myname)
a.drc(myname)
a.lvs(myname)
a.signoff(myname) #blocks inside


