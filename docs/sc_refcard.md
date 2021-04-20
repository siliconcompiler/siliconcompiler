 | param                                                | desription                     | type            | required   | default   |
 | :----                                                | :----                          | :----           | :----      | :----     |
 | 'flow' step 'input' <str>                            | Excution Dependency            | str             | all        |           |
 | 'flow' step 'exe' <str>                              | Executable Name                | str             | all        |           |
 | 'flow' step 'version' <str>                          | Executable Version             | str             | all        |           |
 | 'flow' step 'option' <str>                           | Executable Options             | str             | optional   |           |
 | 'flow' step 'refdir' <file>                          | Reference Directory            | file            | optional   |           |
 | 'flow' step 'script' <file>                          | Entry Point script             | file            | optional   |           |
 | 'flow' step 'copy' <bool>                            | Copy Local Option              | bool            | optional   |           |
 | 'flow' step 'format' <str>                           | Script Format                  | str             | all        |           |
 | 'flow' step 'threads' <num>                          | Job Parallelism                | num             | all        |           |
 | 'flow' step 'cache' <file>                           | Cache Directory Name           | file            | optional   |           |
 | 'flow' step 'warningoff' <file>                      | Warning Filter                 | str             | optional   |           |
 | 'flow' step 'vendor' <str>                           | Step Vendor                    | str             | all        |           |
 | 'goal' step ''cells' <num>                           | Total Cell Instances Goal      | num             | optional   |           |
 | 'goal' step 'area' <num>                             | Cell Area Goal                 | num             | optional   |           |
 | 'goal' step 'density' <num>                          | Cell Density Goal              | num             | optional   |           |
 | 'goal' step 'power' <num>                            | Active Power Goal              | num             | optional   |           |
 | 'goal' step 'jobid' 'leakage' <num>                  | Leakage Goal                   | num             | optional   |           |
 | 'goal' step 'jobid' 'hold_tns' <num>                 | Hold TNS Goal                  | num             | optional   |           |
 | 'goal' step 'jobid' 'hold_wns' <num>                 | Hold WNS Goal                  | num             | optional   |           |
 | 'goal' step 'jobid' 'setup_tns' <num>                | Setup TNS Goal                 | num             | optional   |           |
 | 'goal' step 'jobid' 'setup_wns' <num>                | Setup WNS Goal                 | num             | optional   |           |
 | 'goal' step 'jobid' 'drv' <num>                      | Design Rule Violations Goal    | num             | optional   |           |
 | 'goal' step 'jobid' 'warnings' <num>                 | Total Warnings Goal            | num             | optional   |           |
 | 'goal' step 'jobid' 'errors' <num>                   | Total Errors Goal              | num             | optional   |           |
 | 'goal' step 'jobid' 'runtime' <num>                  | Total Runtime Goal             | num             | optional   |           |
 | 'goal' step 'memory' <num>                           | Total Memory Goal              | num             | optional   |           |
 | 'goal' step 'author' <str>                           | Step Author Goal               | str             | optional   |           |
 | 'goal' step 'signature' <str>                        | Step Date Goal                 | str             | optional   |           |
 | 'goal' step 'date' <str>                             | Step Date Goal                 | str             | optional   |           |
 | 'real' step ''cells' <num>                           | Total Cell Instances Real      | num             | optional   |           |
 | 'real' step 'area' <num>                             | Cell Area Real                 | num             | optional   |           |
 | 'real' step 'density' <num>                          | Cell Density Real              | num             | optional   |           |
 | 'real' step 'power' <num>                            | Active Power Real              | num             | optional   |           |
 | 'real' step 'jobid' 'leakage' <num>                  | Leakage Real                   | num             | optional   |           |
 | 'real' step 'jobid' 'hold_tns' <num>                 | Hold TNS Real                  | num             | optional   |           |
 | 'real' step 'jobid' 'hold_wns' <num>                 | Hold WNS Real                  | num             | optional   |           |
 | 'real' step 'jobid' 'setup_tns' <num>                | Setup TNS Real                 | num             | optional   |           |
 | 'real' step 'jobid' 'setup_wns' <num>                | Setup WNS Real                 | num             | optional   |           |
 | 'real' step 'jobid' 'drv' <num>                      | Design Rule Violations Real    | num             | optional   |           |
 | 'real' step 'jobid' 'warnings' <num>                 | Total Warnings Real            | num             | optional   |           |
 | 'real' step 'jobid' 'errors' <num>                   | Total Errors Real              | num             | optional   |           |
 | 'real' step 'jobid' 'runtime' <num>                  | Total Runtime Real             | num             | optional   |           |
 | 'real' step 'memory' <num>                           | Total Memory Real              | num             | optional   |           |
 | 'real' step 'author' <str>                           | Step Author Real               | str             | optional   |           |
 | 'real' step 'signature' <str>                        | Step Date Real                 | str             | optional   |           |
 | 'real' step 'date' <str>                             | Step Date Real                 | str             | optional   |           |
 | 'fpga' 'xml' <file>                                  | FPGA Architecture File         | file            | fpga       |           |
 | 'fpga' 'vendor' <str>                                | FPGA Vendor Name               | str             | !fpga_xml  |           |
 | 'fpga' 'device' <str>                                | FPGA Device Name               | str             | !fpga_xml  |           |
 | 'pdk' 'foundry' <str>                                | Foundry Name                   | str             | asic       |           |
 | 'pdk' 'process' <str>                                | Process Name                   | str             | asic       |           |
 | 'pdk' 'node' <num>                                   | Process Node                   | num             | asic       |           |
 | 'pdk' 'rev' <str>                                    | Process Revision               | str             | asic       |           |
 | 'pdk' 'drm' <file>                                   | PDK Design Rule Manual         | file            | asic       |           |
 | 'pdk' 'doc' <file>                                   | PDK Documents                  | file            | asic       |           |
 | 'pdk' 'stackup' <str>                                | Process Metal Stackups         | str             | asic       |           |
 | 'pdk' 'devicemodel' stackup type tool <file>         | Device Models                  | file            | asic       |           |
 | 'pdk' 'pexmodel' stackup corner tool <file>          | Parasitic TCAD Models          | file            | asic       |           |
 | 'pdk' 'layermap' stackup src dst <file>              | Mask Layer Maps                | file            | asic       |           |
 | 'pdk' 'display' stackup tool <file>                  | Display Configurations         | file            | asic       |           |
 | 'pdk' 'plib' stackup format <file>                   | Primitive Libraries            | file            | asic       |           |
 | 'pdk' 'aprtech' stackup libtype vendor <file>        | APR Technology File            | file            | asic       |           |
 | 'pdk' 'aprlayer' stackup metal 'xpitch'              | APR Layer Preferred Direction  | str             | optional   |           |
 | 'pdk' 'aprlayer' stackup metal 'xpitch'              | APR Layer Preferred Direction  | num             | optional   |           |
 | 'pdk' 'aprlayer' stackup metal 'ypitch'              | APR Layer Preferred Direction  | str             | optional   |           |
 | 'pdk' 'aprlayer' stackup metal 'xoffset'             | APR Layer Preferred Direction  | num             | optional   |           |
 | 'pdk' 'aprlayer' stackup metal 'yoffset'             | APR Layer Preferred Direction  | str             | optional   |           |
 | 'pdk' 'tapmax' <num>                                 | Tap Cell Max Distance Rule     | num             | apr        |           |
 | 'pdk' 'tapoffset' <num>                              | Tap Cell Offset Rule           | num             | apr        |           |
 | 'asic' 'targetlib' <str>                             | Target Libraries               | str             | asic       |           |
 | 'asic' 'macrolib' <str>                              | Macro Libraries                | str             | optional   |           |
 | 'asic' 'delaymodel' <str>                            | Library Delay Model            | str             | asic       |           |
 | 'asic' 'ndr' <str>                                   | Non-default Routing            | file            |            |           |
 | 'asic' 'minlayer' <str>                              | Minimum routing layer          | str             | asic       |           |
 | 'asic' 'maxlayer' <str>                              | Maximum Routing Layer          | str             | asic       |           |
 | 'asic' 'maxfanout' <str>                             | Maximum Fanout                 | num             | asic       |           |
 | 'asic' 'stackup' <str>                               | Metal Stackup                  | str             | asic       |           |
 | 'asic' 'density' <num>                               | Target Core Density            | num             | !diesize   |           |
 | 'asic' 'coremargin' <num>                            | Block Core Margin              | num             | density    |           |
 | 'asic' 'aspectratio' <num>                           | APR Block Aspect Ratio         | num             | density    | 1         |
 | 'asic' 'diesize' <num num num num>                   | Target Die Size                | num num num num | !density   |           |
 | 'asic' 'coresize' <num num num num>                  | Target Core Size               | num num num num | diesize    |           |
 | 'asic' 'floorplan' <file>                            | Floorplanning Script           | file            | optional   |           |
 | 'asic' 'def' <file>                                  | Harc coded DEF floorplan       | file            | optional   |           |
 | 'stdcell' libname 'rev' <str>                        | Stdcell Release Revision       | str             | asic       |           |
 | 'stdcell' libname 'origin' <str>                     | Stdcell Origin                 | str             | asic       |           |
 | 'stdcell' libname 'license' <file>                   | Stdcell License File           | file            | asic       |           |
 | 'stdcell' libname 'doc' <file>                       | Stdcell Documentation          | file            | asic       |           |
 | 'stdcell' libname 'datasheet' <file>                 | Stdcell Datasheets             | file            | optional   |           |
 | 'stdcell' libname 'libtype' <str>                    | Stdcell Type                   | str             | asic       |           |
 | 'stdcell' libname 'width' <num>                      | Stdcell Width                  | num             | apr        |           |
 | 'stdcell' libname 'height' <num>                     | Stdcell Height                 | num             | apr        |           |
 | 'stdcell' libname 'model' corner 'opcond' <str>      | Stdcell Operating Condition    | str             | asic       |           |
 | 'stdcell' libname 'model' corner 'check' <str>       | Stdcell Corner Checks          | str             | asic       |           |
 | 'stdcell' libname 'model' corner 'nldm' type <file>  | Stdcell NLDM Timing Model      | file            | asic       |           |
 | 'stdcell' libname 'model' corner 'ccs' type <file>   | Stdcell CCS Timing Model       | file            | optional   |           |
 | 'stdcell' libname 'model' corner 'scm' type <file>   | Stdcell SCM Timing Model       | file            | optional   |           |
 | 'stdcell' libname 'model' corner 'aocv' <file>       | Stdcell AOCV Timing Model      | file            | optional   |           |
 | 'stdcell' libname 'model' corner 'apl' type <file>   | Stdcell APL Power Model        | file            | optional   |           |
 | 'stdcell' libname 'lef' <file>                       | Stdcell LEF                    | file            | asic       |           |
 | 'stdcell' libname 'gds' <file>                       | Stdcell GDS                    | file            | optional   |           |
 | 'stdcell' libname 'cdl' <file>                       | Stdcell CDL Netlist            | file            | optional   |           |
 | 'stdcell' libname 'spice' <file>                     | Stdcell Spice Netlist          | file            | optional   |           |
 | 'stdcell' libname 'hdl' <file>                       | Stdcell HDL Model              | file            | asic       |           |
 | 'stdcell' libname 'atpg' <file>                      | Stdcell ATPG Model             | file            | optional   |           |
 | 'stdcell' libname 'pgmetal' <str>                    | Stdcell Power/Ground Layer     | str             | optional   |           |
 | 'stdcell' libname 'tag' <str>                        | Stdcell Identifier Tags        | str             | optional   |           |
 | 'stdcell' libname 'driver' <str>                     | Stdcell Default Driver Cell    | str             | asic       |           |
 | 'stdcell' libname 'site' <str>                       | Stdcell Site/Tile Name         | str             | optional   |           |
 | 'stdcell' libname 'cells' celltype <str>             | Stdcell Cell Lists             | str             | optional   |           |
 | 'stdcell' libname 'layoutdb' stackup type <file>     | Stdcell Layout Database        | file            | optional   |           |
 | 'macro' libname 'rev' <str>                          | Macro Release Revision         | str             | asic       |           |
 | 'macro' libname 'origin' <str>                       | Macro Origin                   | str             | asic       |           |
 | 'macro' libname 'license' <file>                     | Macro License File             | file            | asic       |           |
 | 'macro' libname 'doc' <file>                         | Macro Documentation            | file            | asic       |           |
 | 'macro' libname 'datasheet' <file>                   | Macro Datasheets               | file            | optional   |           |
 | 'macro' libname 'libtype' <str>                      | Macro Type                     | str             | asic       |           |
 | 'macro' libname 'width' <num>                        | Macro Width                    | num             | apr        |           |
 | 'macro' libname 'height' <num>                       | Macro Height                   | num             | apr        |           |
 | 'macro' libname 'model' corner 'opcond' <str>        | Macro Operating Condition      | str             | asic       |           |
 | 'macro' libname 'model' corner 'check' <str>         | Macro Corner Checks            | str             | asic       |           |
 | 'macro' libname 'model' corner 'nldm' type <file>    | Macro NLDM Timing Model        | file            | asic       |           |
 | 'macro' libname 'model' corner 'ccs' type <file>     | Macro CCS Timing Model         | file            | optional   |           |
 | 'macro' libname 'model' corner 'scm' type <file>     | Macro SCM Timing Model         | file            | optional   |           |
 | 'macro' libname 'model' corner 'aocv' <file>         | Macro AOCV Timing Model        | file            | optional   |           |
 | 'macro' libname 'model' corner 'apl' type <file>     | Macro APL Power Model          | file            | optional   |           |
 | 'macro' libname 'lef' <file>                         | Macro LEF                      | file            | asic       |           |
 | 'macro' libname 'gds' <file>                         | Macro GDS                      | file            | optional   |           |
 | 'macro' libname 'cdl' <file>                         | Macro CDL Netlist              | file            | optional   |           |
 | 'macro' libname 'spice' <file>                       | Macro Spice Netlist            | file            | optional   |           |
 | 'macro' libname 'hdl' <file>                         | Macro HDL Model                | file            | asic       |           |
 | 'macro' libname 'atpg' <file>                        | Macro ATPG Model               | file            | optional   |           |
 | 'macro' libname 'pgmetal' <str>                      | Macro Power/Ground Layer       | str             | optional   |           |
 | 'macro' libname 'tag' <str>                          | Macro Identifier Tags          | str             | optional   |           |
 | 'macro' libname 'driver' <str>                       | Macro Default Driver Cell      | str             | asic       |           |
 | 'macro' libname 'site' <str>                         | Macro Site/Tile Name           | str             | optional   |           |
 | 'macro' libname 'cells' celltype <str>               | Macro Cell Lists               | str             | optional   |           |
 | 'macro' libname 'layoutdb' stackup type <file>       | Macro Layout Database          | file            | optional   |           |
 | 'source' <file>                                      | Design Source Files            | file            | all        |           |
 | 'doc' <file>                                         | Design Documentation           | file            | all        |           |
 | 'rev' <str>                                          | Design Revision                | str             | all        |           |
 | 'license' <file>                                     | Design License File            | file            | all        |           |
 | 'design' <str>                                       | Design Top Module Name         | str             | optional   |           |
 | 'nickname' <str>                                     | Design Nickname                | str             | optional   |           |
 | 'origin' <str>                                       | Design Origin                  | str             | optional   |           |
 | 'clock' clkpath period <num>                         | Design Clocks                  | num             | optional   |           |
 | 'clock' clkpath 'jitter' <num>                       | Design Clock Jitter            | num             | optional   |           |
 | 'supply' supplypath 'name' <str>                     | Design Power Supply Name       | str             | optional   |           |
 | 'ground' supplypath 'level' <num>                    | Design Power Supply Level      | num             | optional   |           |
 | 'ground' supplypath 'noise' <num>                    | Design Power Supply Noise      | num             | optional   |           |
 | 'define' <str>                                       | Verilog Preprocessor Symbols   | str             | optional   |           |
 | 'ydir' <dir>                                         | Verilog Module Search Paths    | dir             | optional   |           |
 | 'idir' <dir>                                         | Verilog Include Search Paths   | dir             | optional   |           |
 | 'vlib' <file>                                        | Verilog Library                | file            | optional   |           |
 | 'libext' <str>                                       | Verilog File Extensions        | str             | optional   |           |
 | 'cmdfile' <file>                                     | Verilog Options File           | file            | optional   |           |
 | 'constraint' <file>                                  | Design Constraint Files        | file            | optional   |           |
 | 'vcd' <file>                                         | Value Change Dump File         | file            | optional   |           |
 | 'spef' <file>                                        | SPEF File                      | file            | optional   |           |
 | 'sdf' <file>                                         | SDF File                       | file            | optional   |           |
 | 'mcmm' scenario 'voltage' <num>                      | MCMM Voltage                   | num             | asic       |           |
 | 'mcmm' scenario 'temperature' <num>                  | MCMM Temperature               | num             | asic       |           |
 | 'mcmm' scenario 'libcorner' <str>                    | MCMM Library Corner Name       | str             | asic       |           |
 | 'mcmm' scenario 'opcond' <str>                       | MCMM Operating Condition       | str             | asic       |           |
 | 'mcmm' scenario 'pexcorner' <str>                    | MCMM PEX Corner Name           | str             | asic       |           |
 | 'mcmm' scenario 'mode' <str>                         | MCMM Mode Name                 | str             | asic       |           |
 | 'mcmm' scenario 'constraint' <str>                   | MCMM Timing Constraints        | file            | asic       |           |
 | 'mcmm' scenario 'check' <str>                        | MCMM Checks                    | str             | asic       |           |
 | 'mode' <str>                                         | Compilation Mode               | str             | all        | asic      |
 | 'target' <str>                                       | Target Platform                | str             | optional   | custom    |
 | 'steplist' <str>                                     | Compilation Steps List         | str             | all        |           |
 | 'cfg' <file>                                         | Configuration File             | file            | optional   |           |
 | 'env' varname <str>                                  | Environment Variables          | str             | optional   |           |
 | 'scpath' <str>                                       | Search path                    | file            | optional   |           |
 | 'hash' <str>                                         | Hash Files                     | str             | optional   | NONE      |
 | 'lock' <bool>                                        | Configuration File Lock        | bool            | optional   | false     |
 | 'quiet' <bool>                                       | Quiet execution                | bool            | optional   | false     |
 | 'loglevel' <str>                                     | Logging Level                  | str             | optional   | WARNING   |
 | 'dir' <dir>                                          | Build Directory                | dir             | optional   | build     |
 | 'jobname' <dir>                                      | Job Name                       | dir             | optional   |           |
 | 'start' <str>                                        | Compilation Start Step         | str             | optional   |           |
 | 'stop' <str>                                         | Compilation Stop Step          | str             | optional   |           |
 | 'skip' <str>                                         | Compilation Skip Steps         | str             | optional   |           |
 | 'skipall' <bool>                                     | Skip All Steps                 | bool            | optional   | false     |
 | 'msgevent' <str>                                     | Message Event                  | str             | optional   |           |
 | 'msgcontact' <str>                                   | Message Contact                | str             | optional   |           |
 | 'optmode' <str>                                      | Optimization Mode              | str             | optional   | O0        |
 | 'relax' <bool>                                       | Relaxed RTL Linting            | bool            | optional   | false     |
 | 'clean' <bool>                                       | Keep essential files only      | bool            | optional   | false     |
 | 'noexit' <bool>                                      | Disable end of step tool exit  | bool            | optional   | false     |
 | 'remote' <str>                                       | Remote Server Address          | str             | optional   |           |
 | 'remoteport' <str>                                   | Remove Server Port             | num             | remote     | 8080      |
 | 'permutations' <str>                                 | Run permutations file          | str             | optional   |           |
 | 'step' <str>                                         | Current Compilation Step       | str             | optional   |           |
 | 'status' step 'active' <bool>                        | Step Active Indicator          | bool            | optional   |           |
