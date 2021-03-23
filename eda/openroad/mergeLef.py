#!/usr/bin/env python3

# Script to merge multiple .LEF files into a single file.
# This is necessary because the 'TritonRoute' detailed routing step is
# currently only capable of reading one .LEF file.
#
# Source: The OpenROAD Project.
# https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/master/flow/util/mergeLef.py
#
# License: BSD 3-Clause.
#
#Copyright (c) 2018, The Regents of the University of California
#All rights reserved.
#
#Redistribution and use in source and binary forms, with or without
#modification, are permitted provided that the following conditions are met:
#
#* Redistributions of source code must retain the above copyright notice, this
#  list of conditions and the following disclaimer.
#
#* Redistributions in binary form must reproduce the above copyright notice,
#  this list of conditions and the following disclaimer in the documentation
#  and/or other materials provided with the distribution.
#
#* Neither the name of the copyright holder nor the names of its
#  contributors may be used to endorse or promote products derived from
#  this software without specific prior written permission.
#
#THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
#AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
#IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
#FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
#DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
#CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
#OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import re
import sys
import os
import argparse  # argument parsing

# WARNING: this script expects the tech lef first

# Parse and validate arguments
# ==============================================================================
parser = argparse.ArgumentParser(
    description='Merges lefs together')
parser.add_argument('--inputLef', '-i', required=True,
                    help='Input Lef', nargs='+')
parser.add_argument('--outputLef', '-o', required=True,
                    help='Output Lef')
args = parser.parse_args()


print(os.path.basename(__file__),": Merging LEFs")

f = open(args.inputLef[0])
content = f.read()
f.close()


# Using a set so we get unique entries
propDefinitions = set()

# Remove Last line ending the library
content = re.sub("END LIBRARY","",content)

# Iterate through additional lefs
for lefFile in args.inputLef[1:]:
  f = open(lefFile)
  snippet = f.read()
  f.close()

  # Match the sites
  pattern = r"(^SITE (\S+).*?END\s\2)"
  m = re.findall(pattern, snippet, re.M | re.DOTALL)

  print(os.path.basename(lefFile) + ": SITEs matched found: " + str(len(m)))
  for groups in m:
    content += "\n" + groups[0]


  # Match the macros
  pattern = r"(^MACRO (\S+).*?END\s\2)"
  m = re.findall(pattern, snippet, re.M | re.DOTALL)

  print(os.path.basename(lefFile) + ": MACROs matched found: " + str(len(m)))
  for groups in m:
    content += "\n" + groups[0]

  # Match the property definitions
  pattern = r"^(PROPERTYDEFINITIONS)(.*?)(END PROPERTYDEFINITIONS)"
  m = re.search(pattern, snippet, re.M | re.DOTALL)

  if m:
    print(os.path.basename(lefFile) + ": PROPERTYDEFINITIONS found")
    propDefinitions.update(map(str.strip,m.group(2).split("\n")))


# Add Last line ending the library
content += "\nEND LIBRARY"

# Update property definitions

# Find property definitions in base lef
pattern = r"^(PROPERTYDEFINITIONS)(.*?)(END PROPERTYDEFINITIONS)"
m = re.search(pattern, content, re.M | re.DOTALL)
if m:
  print(os.path.basename(lefFile) + ": PROPERTYDEFINITIONS found in base lef")
  propDefinitions.update(map(str.strip,m.group(2).split("\n")))


replace = r"\1" + "\n".join(propDefinitions) + r"\n\3"
content = re.sub(pattern, replace, content, 0, re.M | re.DOTALL)

# Save the merged lef
f = open(args.outputLef, "w")
f.write(content)
f.close()

print(os.path.basename(__file__),": Merging LEFs complete")
