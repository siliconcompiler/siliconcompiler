# SPDX-FileCopyrightText: 2020 Efabless Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# SPDX-License-Identifier: Apache-2.0

source ./sc_manifest.tcl

set sc_step [sc_cfg_get arg step]
set sc_index [sc_cfg_get arg index]
set sc_task $sc_step

set sc_design [sc_top]
set sc_macrolibs [sc_get_asic_libraries macro]
set sc_stackup [sc_cfg_get option stackup]

foreach sc_lef [sc_cfg_tool_task_get file read_lef] {
    lef read $sc_lef
}

gds noduplicates true

if { [file exists "inputs/$sc_design.gds"] } {
    set gds_path "inputs/$sc_design.gds"
} else {
    set gds_path [sc_cfg_get input layout gds]
}

gds read $gds_path
puts $sc_design.gds
set fout [open reports/$sc_design.drc w]
set oscale [cif scale out]
set cell_name $sc_design
magic::suspendall
puts stdout "\[INFO\]: Loading ${sc_design}\n"
flush stdout
load $sc_design
select top cell
drc euclidean on
drc style drc(full)
drc check
set drcresult [drc listall why]
set count 0
puts $fout "$sc_design"
puts $fout "----------------------------------------"
foreach {errtype coordlist} $drcresult {
    puts $fout $errtype
    puts $fout "----------------------------------------"
    foreach coord $coordlist {
        set bllx [expr { $oscale * [lindex $coord 0] }]
        set blly [expr { $oscale * [lindex $coord 1] }]
        set burx [expr { $oscale * [lindex $coord 2] }]
        set bury [expr { $oscale * [lindex $coord 3] }]
        set coords [format " %.3f %.3f %.3f %.3f" $bllx $blly $burx $bury]
        puts $fout "$coords"
        incr count
    }
    puts $fout "----------------------------------------"
}

puts $fout "\[INFO\]: COUNT: $count"
puts $fout "\[INFO\]: Should be divided by 3 or 4"

puts $fout ""
close $fout

puts stdout "\[INFO\]: COUNT: $count"
puts stdout "\[INFO\]: Should be divided by 3 or 4"
puts stdout "\[INFO\]: DRC Checking DONE (outputs/${sc_design}.drc)"
flush stdout

puts stdout "\[INFO\]: Saving mag view with DRC errors(outputs/${sc_design}.drc.mag)"
# WARNING: changes the name of the cell; keep as last step
save outputs/${sc_design}.drc.mag
puts stdout "\[INFO\]: Saved"

exit 0
