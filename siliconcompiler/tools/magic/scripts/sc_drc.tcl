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

foreach sc_lef [sc_cfg_tool_task_get var read_lef] {
    puts "Reading LEF $sc_lef"
    lef read $sc_lef
}

gds noduplicates true

if { [file exists "inputs/${sc_topmodule}.gds"] } {
    set gds_path "inputs/${sc_topmodule}.gds"
} else {
    set gds_path []
    foreach fileset [sc_cfg_get option fileset] {
        foreach file [sc_cfg_get_fileset $sc_designlib $fileset gds] {
            lappend gds_path $file
        }
    }
}

foreach gds $gds_path {
    puts "Reading: ${gds}"
    gds read $gds
}

set fout [open reports/${sc_topmodule}.drc w]
set oscale [cif scale out]
set cell_name $sc_topmodule
magic::suspendall
puts stdout "\[INFO\]: Loading ${sc_topmodule}\n"
flush stdout
load $sc_topmodule
select top cell
drc euclidean on
drc style drc(full)
drc check
set drcresult [drc listall why]
set count 0
puts $fout "$sc_topmodule"
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

puts "\[INFO\]: COUNT: $count"
puts "\[INFO\]: Should be divided by 3 or 4"
puts "\[INFO\]: DRC Checking DONE (outputs/${sc_topmodule}.drc)"

puts "\[INFO\]: Saving mag view with DRC errors (outputs/${sc_topmodule}.drc.mag)"
# WARNING: changes the name of the cell; keep as last step
save outputs/${sc_topmodule}.drc.mag
puts "\[INFO\]: Saved"

exit 0
