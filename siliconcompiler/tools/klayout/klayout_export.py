# KLayout script to export a .GDS file from a .DEF-formatted design.
#
# Source: The OpenROAD Project.
# https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/master/flow/util/def2stream.py
#
# License: BSD 3-Clause.
#
# Copyright (c) 2018, The Regents of the University of California
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#  list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#  this list of conditions and the following disclaimer in the documentation
#  and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#  contributors may be used to endorse or promote products derived from
#  this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import pya
import re
import json
import copy
import os
import sys
import fnmatch


def gds_export(design_name, in_def, in_files, out_file, tech, allow_missing, config_file='',
               seal_file='',
               timestamps=True):
    # Expand layers in json
    def expand_cfg_layers(cfg):
        layers = cfg['layers']
        expand = [layer for layer in layers if 'layers' in layers[layer]]
        for layer in expand:
            for _, (name, num) in enumerate(zip(layers[layer]['names'],
                                                layers[layer]['layers'])):
                new_layer = copy.deepcopy(layers[layer])
                del new_layer['names']
                new_layer['name'] = name
                del new_layer['layers']
                new_layer['layer'] = num
                layers[name] = new_layer
            del layers[layer]

    def read_cfg():
        print('INFO: Reading config file: ' + config_file)
        with open(config_file, 'r') as f:
            cfg = json.load(f)

        expand_cfg_layers(cfg)
        cfg = cfg['layers']  # ignore the rest

        # Map gds layers & datatype to KLayout indices
        # These are arrays for the different mask numbers
        for layer, vals in cfg.items():
            layer = vals['layer']
            for key in ('opc', 'non-opc'):
                if key not in vals:
                    continue
                data = vals[key]
                if isinstance(data['datatype'], int):
                    data['datatype'] = [data['datatype']]  # convert to array
                data['klayout'] = [main_layout.find_layer(layer, datatype)
                                   for datatype in data['datatype']]

        return cfg

    # match a line like:
    # - LAYER M2 + MASK 2 + OPC RECT ( 3000 3000 ) ( 5000 5000 ) ;
    rect_pat = re.compile(r'''
        \s*\-\ LAYER\ (?P<layer>\S+)  # The layer name
        (?:                           # Non-capturing group
        \s+\+\ MASK\ (?P<mask>\d+)    # Mask, None if absent
        )?
        (?P<opc>                      # OPC, None if absent
        \s+\+\ OPC
        )?
        \s+RECT\
        \(\ (?P<xlo>\d+)\ (?P<ylo>\d+)\ \)\   # rect lower-left pt
        \(\ (?P<xhi>\d+)\ (?P<yhi>\d+)\ \)\ ; # rect upper-right pt
        ''', re.VERBOSE)

    def read_fills(top):
        if config_file == '':
            print('[WARNING] no fill config file specified')
            return
        # KLayout doesn't support FILL in DEF so we have to side load them :(
        cfg = read_cfg()
        in_fills = False
        units = None
        with open(in_def) as fp:
            for line in fp:
                if in_fills:
                    if re.match('END FILLS', line):
                        break  # done with fills; don't care what follows
                    m = re.match(rect_pat, line)
                    if not m:
                        raise Exception('Unrecognized fill: ' + line)
                    opc_type = 'opc' if m.group('opc') else 'non-opc'
                    mask = m.group('mask')
                    if not mask:  # uncolored just uses first entry
                        mask = 0
                    else:
                        mask = int(mask) - 1  # DEF is 1-based indexing
                    layer = cfg[m.group('layer')][opc_type]['klayout'][mask]
                    xlo = int(m.group('xlo')) / units
                    ylo = int(m.group('ylo')) / units
                    xhi = int(m.group('xhi')) / units
                    yhi = int(m.group('yhi')) / units
                    top.shapes(layer).insert(pya.DBox(xlo, ylo, xhi, yhi))
                elif re.match(r'FILLS \d+ ;', line):
                    in_fills = True
                elif not units:
                    m = re.match(r'UNITS DISTANCE MICRONS (\d+)', line)
                    if m:
                        units = float(m.group(1))

    # Load def file
    main_layout = pya.Layout()
    main_layout.technology_name = tech.name
    main_layout.read(in_def, tech.load_layout_options)

    # List cells
    def_cells = []
    for def_cell in main_layout.each_cell():
        def_cells.append(def_cell.name)

    def_cells.remove(design_name)
    # Remove vias
    def_cells = sorted([cell for cell in def_cells if not cell.startswith("VIA_")])
    print(f"[INFO] Read in {len(def_cells)} cells from DEF file")
    for cell in def_cells:
        print(f"  [INFO] DEF cell: {cell}")

    # Load in the gds to merge
    print("[INFO] Merging GDS/OAS files...")
    for fil in in_files:
        macro_layout = pya.Layout()
        macro_layout.read(fil)
        print(f"[INFO] Read in {fil}")
        for cell in list(def_cells):
            if macro_layout.has_cell(cell):
                subcell = main_layout.cell(cell)
                print(f"  [INFO] Merging in {cell}")
                subcell.copy_tree(macro_layout.cell(cell))
                def_cells.remove(cell)

    # Copy the top level only to a new layout
    print("[INFO] Copying toplevel cell '{0}'".format(design_name))
    top_only_layout = pya.Layout()
    top_only_layout.dbu = main_layout.dbu
    top = top_only_layout.create_cell(design_name)
    top.copy_tree(main_layout.cell(design_name))

    read_fills(top)

    print("[INFO] Checking for missing GDS/OAS...")
    missing_cell = False
    for check_cell in def_cells:
        missing_cell = True
        allowed_missing = any([fnmatch.fnmatch(check_cell, pattern) for pattern in allow_missing])
        print(f"[{'WARNING' if allowed_missing else 'ERROR'}] LEF Cell '{check_cell}' has no "
              "matching GDS/OAS cell. Cell will be empty")

    if not missing_cell:
        print("[INFO] All LEF cells have matching GDS/OAS cells")

    print("[INFO] Checking for orphan cell in the final layout...")
    for i in top_only_layout.each_cell():
        if i.name != design_name and i.parent_cells() == 0:
            print("[ERROR] Found orphan cell '{0}'".format(i.name))

    if seal_file:
        top_cell = top_only_layout.top_cell()

        print("[INFO] Reading seal GDS/OAS file...")
        print("\t{0}".format(seal_file))
        top_only_layout.read(seal_file)

        for cell in top_only_layout.top_cells():
            if cell != top_cell:
                print("[INFO] Merging '{0}' as child of '{1}'".format(cell.name, top_cell.name))
                top.insert(pya.CellInstArray(cell.cell_index(), pya.Trans()))

    # Write out the GDS
    print("[INFO] Writing out GDS/OAS '{0}'".format(out_file))
    write_options = pya.SaveLayoutOptions()
    write_options.gds2_write_timestamps = timestamps
    top_only_layout.write(out_file, write_options)


def main():
    # SC_ROOT provided by CLI
    sys.path.append(SC_ROOT)  # noqa: F821

    from schema import Schema  # noqa E402
    from tools.klayout.klayout_utils import technology, get_streams, save_technology  # noqa E402
    from tools.klayout.klayout_show import show  # noqa E402

    schema = Schema(manifest='sc_manifest.json')

    # Extract info from manifest
    sc_step = schema.get('arg', 'step')
    sc_index = schema.get('arg', 'index')
    sc_pdk = schema.get('option', 'pdk')
    sc_flow = schema.get('option', 'flow')
    sc_task = schema.get('flowgraph', sc_flow, sc_step, sc_index, 'task')
    sc_klayout_vars = schema.getkeys('tool', 'klayout', 'task', sc_task, 'var')
    sc_stream = schema.get('tool', 'klayout', 'task', sc_task, 'var', 'stream',
                           step=sc_step, index=sc_index)[0]

    sc_stackup = schema.get('pdk', sc_pdk, 'stackup')[0]

    design = schema.get('option', 'entrypoint')
    if not design:
        design = schema.get('design')

    if schema.valid('input', 'layout', 'def') and schema.get('input', 'layout', 'def',
                                                             step=sc_step, index=sc_index):
        in_def = schema.get('input', 'layout', 'def', step=sc_step, index=sc_index)[0]
    else:
        in_def = os.path.join('inputs', f'{design}.def')
    out_file = os.path.join('outputs', f'{design}.{sc_stream}')

    libs = schema.get('asic', 'logiclib', step=sc_step, index=sc_index)
    if 'macrolib' in schema.getkeys('asic'):
        libs += schema.get('asic', 'macrolib', step=sc_step, index=sc_index)

    in_files = []
    for lib in libs:
        for s in get_streams(schema):
            if schema.valid('library', lib, 'output', sc_stackup, s):
                in_files.extend(schema.get('library', lib, 'output', sc_stackup, s,
                                           step=sc_step, index=sc_index))
                break

    allow_missing = []
    for lib in libs:
        if schema.valid('library', lib, 'option', 'var', 'klayout_allow_missing_cell'):
            patterns = [pattern for pattern in schema.get('library', lib, 'option', 'var',
                                                          'klayout_allow_missing_cell') if pattern]
            allow_missing.extend(patterns)

    if 'timestamps' in sc_klayout_vars:
        sc_timestamps = schema.get('tool', 'klayout', 'task', sc_task, 'var', 'timestamps',
                                   step=sc_step, index=sc_index) == ['true']
    else:
        sc_timestamps = False

    if 'screenshot' in sc_klayout_vars:
        sc_screenshot = schema.get('tool', 'klayout', 'task', sc_task, 'var', 'screenshot',
                                   step=sc_step, index=sc_index) == ['true']
    else:
        sc_screenshot = True

    sc_tech = technology(design, schema)

    gds_export(design, in_def, in_files, out_file, sc_tech, allow_missing,
               config_file='', seal_file='', timestamps=sc_timestamps)

    if sc_screenshot:
        show(schema, sc_tech, out_file, f'outputs/{design}.png', screenshot=True)

    # Save tech files
    save_technology(design, sc_tech)


if __name__ == '__main__':
    main()
