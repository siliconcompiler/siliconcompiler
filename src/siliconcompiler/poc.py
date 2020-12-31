#!/usr/bin/python3
import os
import re
import sys
import multiprocessing
import time

class chip:
    def __init__(self, cfg, name):
        self.id=name                            #name of object
        self.cfg=cfg                            #
        print("***New***")
        lec_running=0
        sta_running=0
        si_running=0
        pi_running=0
        drc_running=0
        lvs_running=0
    #HELPER THREAD
    
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
    def leq(self,dir):
         lec_running=1
         time.sleep(25)
         print("***Logical Equivalence***")
    def sta(self,dir):
         sta_running=1
         time.sleep(20)
         print("***Timing Signoff***")
    def si(self,dir):
         se_running=1
         time.sleep(15)
         print("***Signal Integrity***")
    def pi(self,dir):
         pi_running=1
         time.sleep(10)
         print("***Power Integrity***")
    def drc(self,dir):
         drc_running=1
         time.sleep(5)
         print("***DRC***")
    def lvs(self,dir):
         lvs_running=1
         time.sleep(3)
         print("***LVS***")
    def signoff(self,dir):
         lvs_running=1
         time.sleep(3)
         print("***LVS***")


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
#recommended methodology
##########################################################
a.setup("b")
a.syn("cfg1","setup","syn")
for x in range(10):
    a.place("cfg2","syn","place" + n)
#Check Max, the set d accordingly
a.cts("cfg3","d","e")
a.route("cfg4","e","f")
a.cleanup("cfg5","f","g")
a.export("cfg6","g","h")

##########################################################
#Verification Queue
##########################################################

## Servers, # threads, blocking-nonblocking set by config

#Input is a directory to check
#One directory per design point, easy to tar up


#Setup

#Execution (fluid...)
jobdir="job0/hello"           # job directory (alphanumeric)
a.leq(jobdir)       # logical equivalence check
a.sta(jobdir)       # static timing checks
a.si(jobdir)        # signal integrity check 
a.pi(jobdir)        # power integrity check
a.drc(jobdir)       # drc check
a.lvs(jobdir)       # lvs check
a.signoff(jobdir)   # check that all checks have been run

#if async, the job goes into a queue
#if sync, it 
#everything is a directory
#file names are the same
#separate
#signoff should print out a columnized schedule of progress


