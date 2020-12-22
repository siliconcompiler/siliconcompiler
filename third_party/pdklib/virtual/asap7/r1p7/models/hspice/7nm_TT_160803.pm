* BSD 3-Clause License
* 
* Copyright 2020 Lawrence T. Clark, Vinay Vashishtha, or Arizona State
* University
* 
* Redistribution and use in source and binary forms, with or without
* modification, are permitted provided that the following conditions are met:
* 
* 1. Redistributions of source code must retain the above copyright notice,
* this list of conditions and the following disclaimer.
* 
* 2. Redistributions in binary form must reproduce the above copyright
* notice, this list of conditions and the following disclaimer in the
* documentation and/or other materials provided with the distribution.
* 
* 3. Neither the name of the copyright holder nor the names of its
* contributors may be used to endorse or promote products derived from this
* software without specific prior written permission.
* 
* THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
* AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
* IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
* ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
* LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
* CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
* SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
* INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
* CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
* ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
* POSSIBILITY OF SUCH DAMAGE.

** ASAP TT models v1.0 8/3/16

** Hspice modelcard
.model nmos_lvt nmos level = 72 
************************************************************
*                         general                          *
************************************************************
+version = 107             bulkmod = 1               igcmod  = 1               igbmod  = 0             
+gidlmod = 1               iimod   = 0               geomod  = 1               rdsmod  = 0             
+rgatemod= 0               rgeomod = 0               shmod   = 0               nqsmod  = 0             
+coremod = 0               cgeomod = 0               capmod  = 0               tnom    = 25            
+eot     = 1e-009          eotbox  = 1.4e-007        eotacc  = 1e-010          tfin    = 6.5e-009      
+toxp    = 2.1e-009        nbody   = 1e+022          phig    = 4.307           epsrox  = 3.9           
+epsrsub = 11.9            easub   = 4.05            ni0sub  = 1.1e+016        bg0sub  = 1.17          
+nc0sub  = 2.86e+025       nsd     = 2e+026          ngate   = 0               nseg    = 5             
+l       = 2.1e-008        xl      = 1e-009          lint    = -2e-009         dlc     = 0             
+dlbin   = 0               hfin    = 3.2e-008        deltaw  = 0               deltawcv= 0             
+sdterm  = 0               epsrsp  = 3.9           
+toxg    = 1.80e-009
************************************************************
*                            dc                            *
************************************************************
+cit     = 0               cdsc    = 0.01            cdscd   = 0.01            dvt0    = 0.05          
+dvt1    = 0.475           phin    = 0.05            eta0    = 0.068           dsub    = 0.35          
+k1rsce  = 0               lpe0    = 0               dvtshift= 0               qmfactor= 2.5           
+etaqm   = 0.54            qm0     = 0.001           pqm     = 0.66            u0      = 0.0283        
+etamob  = 2               up      = 0               ua      = 0.55            eu      = 1.2           
+ud      = 0               ucs     = 1               rdswmin = 0               rdsw    = 200           
+wr      = 1               rswmin  = 0               rdwmin  = 0               rshs    = 0             
+rshd    = 0               vsat    = 70000           deltavsat= 0.24            ksativ  = 2             
+mexp    = 4               ptwg    = 30              pclm    = 0.05            pclmg   = 0             
+pdibl1  = 0               pdibl2  = 0.002           drout   = 1               pvag    = 0             
+fpitch  = 2.7e-008        rth0    = 0.225           cth0    = 1.243e-006      wth0    = 2.6e-007      
+lcdscd  = 5e-005          lcdscdr = 5e-005          lrdsw   = 0.2             lvsat   = 0             
************************************************************
*                         leakage                          *
************************************************************
+aigc    = 0.014           bigc    = 0.005           cigc    = 0.25            dlcigs  = 1e-009        
+dlcigd  = 1e-009          aigs    = 0.0115          aigd    = 0.0115          bigs    = 0.00332       
+bigd    = 0.00332         cigs    = 0.35            cigd    = 0.35            poxedge = 1.1           
+agidl   = 1e-012          agisl   = 1e-012          bgidl   = 10000000        bgisl   = 10000000      
+egidl   = 0.35            egisl   = 0.35          
************************************************************
*                            rf                            *
************************************************************
************************************************************
*                         junction                         *
************************************************************
************************************************************
*                       capacitance                        *
************************************************************
+cfs     = 0               cfd     = 0               cgso    = 1.6e-010        cgdo    = 1.6e-010      
+cgsl    = 0               cgdl    = 0               ckappas = 0.6             ckappad = 0.6           
+cgbo    = 0               cgbl    = 0             
************************************************************
*                       temperature                        *
************************************************************
+tbgasub = 0.000473        tbgbsub = 636             kt1     = 0               kt1l    = 0             
+ute     = -0.7            utl     = 0               ua1     = 0.001032        ud1     = 0             
+ucste   = -0.004775       at      = 0.001           ptwgt   = 0.004           tmexp   = 0             
+prt     = 0               tgidl   = -0.007          igt     = 2.5           
************************************************************
*                          noise                           *
************************************************************
**

** Hspice modelcard
.model nmos_rvt nmos level = 72 
************************************************************
*                         general                          *
************************************************************
+version = 107             bulkmod = 1               igcmod  = 1               igbmod  = 0             
+gidlmod = 1               iimod   = 0               geomod  = 1               rdsmod  = 0             
+rgatemod= 0               rgeomod = 0               shmod   = 0               nqsmod  = 0             
+coremod = 0               cgeomod = 0               capmod  = 0               tnom    = 25            
+eot     = 1e-009          eotbox  = 1.4e-007        eotacc  = 1e-010          tfin    = 6.5e-009      
+toxp    = 2.1e-009        nbody   = 1e+022          phig    = 4.372           epsrox  = 3.9           
+epsrsub = 11.9            easub   = 4.05            ni0sub  = 1.1e+016        bg0sub  = 1.17          
+nc0sub  = 2.86e+025       nsd     = 2e+026          ngate   = 0               nseg    = 5             
+l       = 2.1e-008        xl      = 1e-009          lint    = -2e-009         dlc     = 0             
+dlbin   = 0               hfin    = 3.2e-008        deltaw  = 0               deltawcv= 0             
+sdterm  = 0               epsrsp  = 3.9           
+toxg    = 1.80e-009
************************************************************
*                            dc                            *
************************************************************
+cit     = 0               cdsc    = 0.01            cdscd   = 0.01            dvt0    = 0.05          
+dvt1    = 0.48            phin    = 0.05            eta0    = 0.062           dsub    = 0.35          
+k1rsce  = 0               lpe0    = 0               dvtshift= 0               qmfactor= 2.5           
+etaqm   = 0.54            qm0     = 0.001           pqm     = 0.66            u0      = 0.0252        
+etamob  = 2               up      = 0               ua      = 0.55            eu      = 1.2           
+ud      = 0               ucs     = 1               rdswmin = 0               rdsw    = 200           
+wr      = 1               rswmin  = 0               rdwmin  = 0               rshs    = 0             
+rshd    = 0               vsat    = 70000           deltavsat= 0.28            ksativ  = 2             
+mexp    = 4               ptwg    = 30              pclm    = 0.05            pclmg   = 0             
+pdibl1  = 0               pdibl2  = 0.002           drout   = 1               pvag    = 0             
+fpitch  = 2.7e-008        rth0    = 0.225           cth0    = 1.243e-006      wth0    = 2.6e-007      
+lcdscd  = 5e-005          lcdscdr = 5e-005          lrdsw   = 0.2             lvsat   = 0             
************************************************************
*                         leakage                          *
************************************************************
+aigc    = 0.014           bigc    = 0.005           cigc    = 0.25            dlcigs  = 1e-009        
+dlcigd  = 1e-009          aigs    = 0.0115          aigd    = 0.0115          bigs    = 0.00332       
+bigd    = 0.00332         cigs    = 0.35            cigd    = 0.35            poxedge = 1.1           
+agidl   = 1e-012          agisl   = 1e-012          bgidl   = 10000000        bgisl   = 10000000      
+egidl   = 0.35            egisl   = 0.35          
************************************************************
*                            rf                            *
************************************************************
************************************************************
*                         junction                         *
************************************************************
************************************************************
*                       capacitance                        *
************************************************************
+cfs     = 0               cfd     = 0               cgso    = 1.6e-010        cgdo    = 1.6e-010      
+cgsl    = 0               cgdl    = 0               ckappas = 0.6             ckappad = 0.6           
+cgbo    = 0               cgbl    = 0             
************************************************************
*                       temperature                        *
************************************************************
+tbgasub = 0.000473        tbgbsub = 636             kt1     = 0               kt1l    = 0             
+ute     = -0.7            utl     = 0               ua1     = 0.001032        ud1     = 0             
+ucste   = -0.004775       at      = 0.001           ptwgt   = 0.004           tmexp   = 0             
+prt     = 0               tgidl   = -0.007          igt     = 2.5           
************************************************************
*                          noise                           *
************************************************************
**

** Hspice modelcard
.model nmos_slvt nmos level = 72 
************************************************************
*                         general                          *
************************************************************
+version = 107             bulkmod = 1               igcmod  = 1               igbmod  = 0             
+gidlmod = 1               iimod   = 0               geomod  = 1               rdsmod  = 0             
+rgatemod= 0               rgeomod = 0               shmod   = 0               nqsmod  = 0             
+coremod = 0               cgeomod = 0               capmod  = 0               tnom    = 25            
+eot     = 1e-009          eotbox  = 1.4e-007        eotacc  = 1e-010          tfin    = 6.5e-009      
+toxp    = 2.1e-009        nbody   = 1e+022          phig    = 4.2466          epsrox  = 3.9           
+epsrsub = 11.9            easub   = 4.05            ni0sub  = 1.1e+016        bg0sub  = 1.17          
+nc0sub  = 2.86e+025       nsd     = 2e+026          ngate   = 0               nseg    = 5             
+l       = 2.1e-008        xl      = 1e-009          lint    = -2e-009         dlc     = 0             
+dlbin   = 0               hfin    = 3.2e-008        deltaw  = 0               deltawcv= 0             
+sdterm  = 0               epsrsp  = 3.9           
+toxg    = 1.80e-009
************************************************************
*                            dc                            *
************************************************************
+cit     = 0               cdsc    = 0.01            cdscd   = 0.01            dvt0    = 0.05          
+dvt1    = 0.47            phin    = 0.05            eta0    = 0.07            dsub    = 0.35          
+k1rsce  = 0               lpe0    = 0               dvtshift= 0               qmfactor= 2.5           
+etaqm   = 0.54            qm0     = 0.001           pqm     = 0.66            u0      = 0.0303        
+etamob  = 2               up      = 0               ua      = 0.55            eu      = 1.2           
+ud      = 0               ucs     = 1               rdswmin = 0               rdsw    = 200           
+wr      = 1               rswmin  = 0               rdwmin  = 0               rshs    = 0             
+rshd    = 0               vsat    = 70000           deltavsat= 0.2             ksativ  = 2             
+mexp    = 4               ptwg    = 30              pclm    = 0.05            pclmg   = 0             
+pdibl1  = 0               pdibl2  = 0.002           drout   = 1               pvag    = 0             
+fpitch  = 2.7e-008        rth0    = 0.225           cth0    = 1.243e-006      wth0    = 2.6e-007      
+lcdscd  = 5e-005          lcdscdr = 5e-005          lrdsw   = 0.2             lvsat   = 0             
************************************************************
*                         leakage                          *
************************************************************
+aigc    = 0.014           bigc    = 0.005           cigc    = 0.25            dlcigs  = 1e-009        
+dlcigd  = 1e-009          aigs    = 0.0115          aigd    = 0.0115          bigs    = 0.00332       
+bigd    = 0.00332         cigs    = 0.35            cigd    = 0.35            poxedge = 1.1           
+agidl   = 1e-012          agisl   = 1e-012          bgidl   = 10000000        bgisl   = 10000000      
+egidl   = 0.35            egisl   = 0.35          
************************************************************
*                            rf                            *
************************************************************
************************************************************
*                         junction                         *
************************************************************
************************************************************
*                       capacitance                        *
************************************************************
+cfs     = 0               cfd     = 0               cgso    = 1.6e-010        cgdo    = 1.6e-010      
+cgsl    = 0               cgdl    = 0               ckappas = 0.6             ckappad = 0.6           
+cgbo    = 0               cgbl    = 0             
************************************************************
*                       temperature                        *
************************************************************
+tbgasub = 0.000473        tbgbsub = 636             kt1     = 0               kt1l    = 0             
+ute     = -0.7            utl     = 0               ua1     = 0.001032        ud1     = 0             
+ucste   = -0.004775       at      = 0.001           ptwgt   = 0.004           tmexp   = 0             
+prt     = 0               tgidl   = -0.007          igt     = 2.5           
************************************************************
*                          noise                           *
************************************************************
**

** Hspice modelcard
.model nmos_sram nmos level = 72 
************************************************************
*                         general                          *
************************************************************
+version = 107             bulkmod = 1               igcmod  = 1               igbmod  = 0             
+gidlmod = 1               iimod   = 0               geomod  = 1               rdsmod  = 0             
+rgatemod= 0               rgeomod = 0               shmod   = 0               nqsmod  = 0             
+coremod = 0               cgeomod = 0               capmod  = 0               tnom    = 25            
+eot     = 1e-009          eotbox  = 1.4e-007        eotacc  = 1e-010          tfin    = 6.5e-009      
+toxp    = 2.1e-009        nbody   = 1e+022          phig    = 4.45            epsrox  = 3.9           
+epsrsub = 11.9            easub   = 4.05            ni0sub  = 1.1e+016        bg0sub  = 1.17          
+nc0sub  = 2.86e+025       nsd     = 2e+026          ngate   = 0               nseg    = 5             
+l       = 2.1e-008        xl      = 1e-009          lint    = -3e-009         dlc     = 0             
+dlbin   = 0               hfin    = 3.2e-008        deltaw  = 0               deltawcv= 0             
+sdterm  = 0               epsrsp  = 3.9           
+toxg    = 1.80e-009
************************************************************
*                            dc                            *
************************************************************
+cit     = 0               cdsc    = 0.01            cdscd   = 0.01            dvt0    = 0.05          
+dvt1    = 0.48            phin    = 0.05            eta0    = 0.062           dsub    = 0.35          
+k1rsce  = 0               lpe0    = 0               dvtshift= 0               qmfactor= 2.5           
+etaqm   = 0.54            qm0     = 0.001           pqm     = 0.66            u0      = 0.025         
+etamob  = 2               up      = 0               ua      = 0.55            eu      = 1.2           
+ud      = 0               ucs     = 1               rdswmin = 0               rdsw    = 200           
+wr      = 1               rswmin  = 0               rdwmin  = 0               rshs    = 0             
+rshd    = 0               vsat    = 70000           deltavsat= 0.28            ksativ  = 2             
+mexp    = 4               ptwg    = 30              pclm    = 0.05            pclmg   = 0             
+pdibl1  = 0               pdibl2  = 0.002           drout   = 1               pvag    = 0             
+fpitch  = 2.7e-008        rth0    = 0.225           cth0    = 1.243e-006      wth0    = 2.6e-007      
+lcdscd  = 5e-005          lcdscdr = 5e-005          lrdsw   = 0.2             lvsat   = 0             
************************************************************
*                         leakage                          *
************************************************************
+aigc    = 0.014           bigc    = 0.005           cigc    = 0.25            dlcigs  = 1e-009        
+dlcigd  = 1e-009          aigs    = 0.0115          aigd    = 0.0115          bigs    = 0.00332       
+bigd    = 0.00332         cigs    = 0.35            cigd    = 0.35            poxedge = 1.1           
+agidl   = 6e-013          agisl   = 1e-012          bgidl   = 10000000        bgisl   = 10000000      
+egidl   = 0.35            egisl   = 0.35          
************************************************************
*                            rf                            *
************************************************************
************************************************************
*                         junction                         *
************************************************************
************************************************************
*                       capacitance                        *
************************************************************
+cfs     = 0               cfd     = 0               cgso    = 1.45e-010       cgdo    = 1.45e-010     
+cgsl    = 0               cgdl    = 0               ckappas = 0.6             ckappad = 0.6           
+cgbo    = 0               cgbl    = 0             
************************************************************
*                       temperature                        *
************************************************************
+tbgasub = 0.000473        tbgbsub = 636             kt1     = 0               kt1l    = 0             
+ute     = -0.7            utl     = 0               ua1     = 0.001032        ud1     = 0             
+ucste   = -0.004775       at      = 0.001           ptwgt   = 0.004           tmexp   = 0             
+prt     = 0               tgidl   = -0.007          igt     = 2.5           
************************************************************
*                          noise                           *
************************************************************
**

** Hspice modelcard
.model pmos_lvt pmos level = 72 
************************************************************
*                         general                          *
************************************************************
+version = 107             bulkmod = 1               igcmod  = 1               igbmod  = 0             
+gidlmod = 1               iimod   = 0               geomod  = 1               rdsmod  = 0             
+rgatemod= 0               rgeomod = 0               shmod   = 0               nqsmod  = 0             
+coremod = 0               cgeomod = 0               capmod  = 0               tnom    = 25            
+eot     = 1e-009          eotbox  = 1.4e-007        eotacc  = 3e-010          tfin    = 6.5e-009      
+toxp    = 2.1e-009        nbody   = 1e+022          phig    = 4.8681          epsrox  = 3.9           
+epsrsub = 11.9            easub   = 4.05            ni0sub  = 1.1e+016        bg0sub  = 1.17          
+nc0sub  = 2.86e+025       nsd     = 2e+026          ngate   = 0               nseg    = 5             
+l       = 2.1e-008        xl      = 1e-009          lint    = -2.5e-009       dlc     = 0             
+dlbin   = 0               hfin    = 3.2e-008        deltaw  = 0               deltawcv= 0             
+sdterm  = 0               epsrsp  = 3.9           
+toxg    = 1.85e-009
************************************************************
*                            dc                            *
************************************************************
+cit     = 0               cdsc    = 0.003469        cdscd   = 0.001486        dvt0    = 0.05          
+dvt1    = 0.38            phin    = 0.05            eta0    = 0.093           dsub    = 0.24          
+k1rsce  = 0               lpe0    = 0               dvtshift= 0               qmfactor= 0             
+etaqm   = 0.54            qm0     = 2.183e-012      pqm     = 0.66            u0      = 0.0227        
+etamob  = 4               up      = 0               ua      = 1.133           eu      = 0.05          
+ud      = 0.0105          ucs     = 0.2672          rdswmin = 0               rdsw    = 200           
+wr      = 1               rswmin  = 0               rdwmin  = 0               rshs    = 0             
+rshd    = 0               vsat    = 60000           deltavsat= 0.2             ksativ  = 1.592         
+mexp    = 2.491           ptwg    = 25              pclm    = 0.01            pclmg   = 1             
+pdibl1  = 800             pdibl2  = 0.005704        drout   = 4.97            pvag    = 200           
+fpitch  = 2.7e-008        rth0    = 0.15            cth0    = 1.243e-006      wth0    = 2.6e-007      
+lcdscd  = 0               lcdscdr = 0               lrdsw   = 1.3             lvsat   = 1441          
************************************************************
*                         leakage                          *
************************************************************
+aigc    = 0.007           bigc    = 0.0015          cigc    = 1               dlcigs  = 5e-009        
+dlcigd  = 5e-009          aigs    = 0.006           aigd    = 0.006           bigs    = 0.001944      
+bigd    = 0.001944        cigs    = 1               cigd    = 1               poxedge = 1.152         
+agidl   = 2e-012          agisl   = 2e-012          bgidl   = 1.5e+008        bgisl   = 1.5e+008      
+egidl   = 1.142           egisl   = 1.142         
************************************************************
*                            rf                            *
************************************************************
************************************************************
*                         junction                         *
************************************************************
************************************************************
*                       capacitance                        *
************************************************************
+cfs     = 0               cfd     = 0               cgso    = 1.6e-010        cgdo    = 1.6e-010      
+cgsl    = 0               cgdl    = 0               ckappas = 0.6             ckappad = 0.6           
+cgbo    = 0               cgbl    = 0             
************************************************************
*                       temperature                        *
************************************************************
+tbgasub = 0.000473        tbgbsub = 636             kt1     = 0               kt1l    = 0             
+ute     = -1.2            utl     = 0               ua1     = 0.001032        ud1     = 0             
+ucste   = -0.004775       at      = 0.001           ptwgt   = 0.004           tmexp   = 0             
+prt     = 0               tgidl   = -0.007          igt     = 2.5           
************************************************************
*                          noise                           *
************************************************************
**

** Hspice modelcard
.model pmos_rvt pmos level = 72 
************************************************************
*                         general                          *
************************************************************
+version = 107             bulkmod = 1               igcmod  = 1               igbmod  = 0             
+gidlmod = 1               iimod   = 0               geomod  = 1               rdsmod  = 0             
+rgatemod= 0               rgeomod = 0               shmod   = 0               nqsmod  = 0             
+coremod = 0               cgeomod = 0               capmod  = 0               tnom    = 25            
+eot     = 1e-009          eotbox  = 1.4e-007        eotacc  = 3e-010          tfin    = 6.5e-009      
+toxp    = 2.1e-009        nbody   = 1e+022          phig    = 4.8108          epsrox  = 3.9           
+epsrsub = 11.9            easub   = 4.05            ni0sub  = 1.1e+016        bg0sub  = 1.17          
+nc0sub  = 2.86e+025       nsd     = 2e+026          ngate   = 0               nseg    = 5             
+l       = 2.1e-008        xl      = 1e-009          lint    = -2.5e-009       dlc     = 0             
+dlbin   = 0               hfin    = 3.2e-008        deltaw  = 0               deltawcv= 0             
+sdterm  = 0               epsrsp  = 3.9           
+toxg    = 1.9e-009
************************************************************
*                            dc                            *
************************************************************
+cit     = 0               cdsc    = 0.003469        cdscd   = 0.001486        dvt0    = 0.05          
+dvt1    = 0.4             phin    = 0.05            eta0    = 0.09            dsub    = 0.24          
+k1rsce  = 0               lpe0    = 0               dvtshift= 0               qmfactor= 0             
+etaqm   = 0.54            qm0     = 2.183e-012      pqm     = 0.66            u0      = 0.0209        
+etamob  = 4               up      = 0               ua      = 1.133           eu      = 0.05          
+ud      = 0.0105          ucs     = 0.2672          rdswmin = 0               rdsw    = 200           
+wr      = 1               rswmin  = 0               rdwmin  = 0               rshs    = 0             
+rshd    = 0               vsat    = 60000           deltavsat= 0.22            ksativ  = 1.592         
+mexp    = 2.491           ptwg    = 25              pclm    = 0.01            pclmg   = 1             
+pdibl1  = 800             pdibl2  = 0.005704        drout   = 4.97            pvag    = 200           
+fpitch  = 2.7e-008        rth0    = 0.15            cth0    = 1.243e-006      wth0    = 2.6e-007      
+lcdscd  = 0               lcdscdr = 0               lrdsw   = 1.3             lvsat   = 1441          
************************************************************
*                         leakage                          *
************************************************************
+aigc    = 0.007           bigc    = 0.0015          cigc    = 1               dlcigs  = 5e-009        
+dlcigd  = 5e-009          aigs    = 0.006           aigd    = 0.006           bigs    = 0.001944      
+bigd    = 0.001944        cigs    = 1               cigd    = 1               poxedge = 1.152         
+agidl   = 2e-012          agisl   = 2e-012          bgidl   = 1.5e+008        bgisl   = 1.5e+008      
+egidl   = 1.142           egisl   = 1.142         
************************************************************
*                            rf                            *
************************************************************
************************************************************
*                         junction                         *
************************************************************
************************************************************
*                       capacitance                        *
************************************************************
+cfs     = 0               cfd     = 0               cgso    = 1.6e-010        cgdo    = 1.6e-010      
+cgsl    = 0               cgdl    = 0               ckappas = 0.6             ckappad = 0.6           
+cgbo    = 0               cgbl    = 0             
************************************************************
*                       temperature                        *
************************************************************
+tbgasub = 0.000473        tbgbsub = 636             kt1     = 0               kt1l    = 0             
+ute     = -1.2            utl     = 0               ua1     = 0.001032        ud1     = 0             
+ucste   = -0.004775       at      = 0.001           ptwgt   = 0.004           tmexp   = 0             
+prt     = 0               tgidl   = -0.007          igt     = 2.5           
************************************************************
*                          noise                           *
************************************************************
**

** Hspice modelcard
.model pmos_slvt pmos level = 72 
************************************************************
*                         general                          *
************************************************************
+version = 107             bulkmod = 1               igcmod  = 1               igbmod  = 0             
+gidlmod = 1               iimod   = 0               geomod  = 1               rdsmod  = 0             
+rgatemod= 0               rgeomod = 0               shmod   = 0               nqsmod  = 0             
+coremod = 0               cgeomod = 0               capmod  = 0               tnom    = 25            
+eot     = 1e-009          eotbox  = 1.4e-007        eotacc  = 3e-010          tfin    = 6.5e-009      
+toxp    = 2.1e-009        nbody   = 1e+022          phig    = 4.9278          epsrox  = 3.9           
+epsrsub = 11.9            easub   = 4.05            ni0sub  = 1.1e+016        bg0sub  = 1.17          
+nc0sub  = 2.86e+025       nsd     = 2e+026          ngate   = 0               nseg    = 5             
+l       = 2.1e-008        xl      = 1e-009          lint    = -2.5e-009       dlc     = 0             
+dlbin   = 0               hfin    = 3.2e-008        deltaw  = 0               deltawcv= 0             
+sdterm  = 0               epsrsp  = 3.9           
+toxg    = 1.8e-009
************************************************************
*                            dc                            *
************************************************************
+cit     = 0               cdsc    = 0.003469        cdscd   = 0.001486        dvt0    = 0.05          
+dvt1    = 0.36            phin    = 0.05            eta0    = 0.094           dsub    = 0.24          
+k1rsce  = 0               lpe0    = 0               dvtshift= 0               qmfactor= 0             
+etaqm   = 0.54            qm0     = 2.183e-012      pqm     = 0.66            u0      = 0.0237        
+etamob  = 4               up      = 0               ua      = 1.133           eu      = 0.05          
+ud      = 0.0105          ucs     = 0.2672          rdswmin = 0               rdsw    = 200           
+wr      = 1               rswmin  = 0               rdwmin  = 0               rshs    = 0             
+rshd    = 0               vsat    = 60000           deltavsat= 0.17            ksativ  = 1.592         
+mexp    = 2.491           ptwg    = 25              pclm    = 0.01            pclmg   = 1             
+pdibl1  = 800             pdibl2  = 0.005704        drout   = 4.97            pvag    = 200           
+fpitch  = 2.7e-008        rth0    = 0.15            cth0    = 1.243e-006      wth0    = 2.6e-007      
+lcdscd  = 0               lcdscdr = 0               lrdsw   = 1.3             lvsat   = 1441          
************************************************************
*                         leakage                          *
************************************************************
+aigc    = 0.007           bigc    = 0.0015          cigc    = 1               dlcigs  = 5e-009        
+dlcigd  = 5e-009          aigs    = 0.006           aigd    = 0.006           bigs    = 0.001944      
+bigd    = 0.001944        cigs    = 1               cigd    = 1               poxedge = 1.152         
+agidl   = 2e-012          agisl   = 2e-012          bgidl   = 1.5e+008        bgisl   = 1.5e+008      
+egidl   = 1.142           egisl   = 1.142         
************************************************************
*                            rf                            *
************************************************************
************************************************************
*                         junction                         *
************************************************************
************************************************************
*                       capacitance                        *
************************************************************
+cfs     = 0               cfd     = 0               cgso    = 1.6e-010        cgdo    = 1.6e-010      
+cgsl    = 0               cgdl    = 0               ckappas = 0.6             ckappad = 0.6           
+cgbo    = 0               cgbl    = 0             
************************************************************
*                       temperature                        *
************************************************************
+tbgasub = 0.000473        tbgbsub = 636             kt1     = 0               kt1l    = 0             
+ute     = -1.2            utl     = 0               ua1     = 0.001032        ud1     = 0             
+ucste   = -0.004775       at      = 0.001           ptwgt   = 0.004           tmexp   = 0             
+prt     = 0               tgidl   = -0.007          igt     = 2.5           
************************************************************
*                          noise                           *
************************************************************
**

** Hspice modelcard
.model pmos_sram pmos level = 72 
************************************************************
*                         general                          *
************************************************************
+version = 107             bulkmod = 1               igcmod  = 1               igbmod  = 0             
+gidlmod = 1               iimod   = 0               geomod  = 1               rdsmod  = 0             
+rgatemod= 0               rgeomod = 0               shmod   = 0               nqsmod  = 0             
+coremod = 0               cgeomod = 0               capmod  = 0               tnom    = 25            
+eot     = 1e-009          eotbox  = 1.4e-007        eotacc  = 3e-010          tfin    = 6.5e-009      
+toxp    = 2.1e-009        nbody   = 1e+022          phig    = 4.78            epsrox  = 3.9           
+epsrsub = 11.9            easub   = 4.05            ni0sub  = 1.1e+016        bg0sub  = 1.17          
+nc0sub  = 2.86e+025       nsd     = 2e+026          ngate   = 0               nseg    = 5             
+l       = 2.1e-008        xl      = 1e-009          lint    = -4.5e-009       dlc     = 0             
+dlbin   = 0               hfin    = 3.2e-008        deltaw  = 0               deltawcv= 0             
+sdterm  = 0               epsrsp  = 3.9           
+toxg    = 1.95e-009
************************************************************
*                            dc                            *
************************************************************
+cit     = 0               cdsc    = 0.002           cdscd   = 0.0008          dvt0    = 0.05          
+dvt1    = 0.4             phin    = 0.05            eta0    = 0.09            dsub    = 0.24          
+k1rsce  = 0               lpe0    = 0               dvtshift= 0               qmfactor= 0             
+etaqm   = 0.54            qm0     = 2.183e-012      pqm     = 0.66            u0      = 0.0209        
+etamob  = 4               up      = 0               ua      = 1.133           eu      = 0.05          
+ud      = 0.0105          ucs     = 0.2672          rdswmin = 0               rdsw    = 200           
+wr      = 1               rswmin  = 0               rdwmin  = 0               rshs    = 0             
+rshd    = 0               vsat    = 60000           deltavsat= 0.22            ksativ  = 1.592         
+mexp    = 2.491           ptwg    = 25              pclm    = 0.01            pclmg   = 1             
+pdibl1  = 800             pdibl2  = 0.005704        drout   = 4.97            pvag    = 200           
+fpitch  = 2.7e-008        rth0    = 0.15            cth0    = 1.243e-006      wth0    = 2.6e-007      
+lcdscd  = 0               lcdscdr = 0               lrdsw   = 1.3             lvsat   = 1441          
************************************************************
*                         leakage                          *
************************************************************
+aigc    = 0.007           bigc    = 0.0015          cigc    = 1               dlcigs  = 5e-009        
+dlcigd  = 5e-009          aigs    = 0.006           aigd    = 0.006           bigs    = 0.001944      
+bigd    = 0.001944        cigs    = 1               cigd    = 1               poxedge = 1.152         
+agidl   = 6e-012          agisl   = 2e-012          bgidl   = 76500000        bgisl   = 1.5e+008      
+egidl   = 1.142           egisl   = 1.142         
************************************************************
*                            rf                            *
************************************************************
************************************************************
*                         junction                         *
************************************************************
************************************************************
*                       capacitance                        *
************************************************************
+cfs     = 0               cfd     = 0               cgso    = 1.45e-010       cgdo    = 1.45e-010     
+cgsl    = 0               cgdl    = 0               ckappas = 0.6             ckappad = 0.6           
+cgbo    = 0               cgbl    = 0             
************************************************************
*                       temperature                        *
************************************************************
+tbgasub = 0.000473        tbgbsub = 636             kt1     = 0               kt1l    = 0             
+ute     = -1.2            utl     = 0               ua1     = 0.001032        ud1     = 0             
+ucste   = -0.004775       at      = 0.001           ptwgt   = 0.004           tmexp   = 0             
+prt     = 0               tgidl   = -0.007          igt     = 2.5           
************************************************************
*                          noise                           *
************************************************************
