import pya
import os
import shutil


def get_streams(schema):
    sc_step = schema.get('arg', 'step')
    sc_index = schema.get('arg', 'index')
    sc_flow = schema.get('option', 'flow')
    sc_task = schema.get('flowgraph', sc_flow, sc_step, sc_index, 'task')

    streams = ('gds', 'oas')
    if schema.valid('tool', 'klayout', 'task', sc_task, 'var', 'stream'):
        sc_stream = schema.get('tool', 'klayout', 'task', sc_task, 'var', 'stream',
                               step=sc_step, index=sc_index)[0]
    else:
        sc_stream = streams[0]
    return [sc_stream, *[s for s in streams if s != sc_stream]]


def technology(design, schema):
    sc_step = schema.get('arg', 'step')
    sc_index = schema.get('arg', 'index')
    sc_pdk = schema.get('option', 'pdk')

    if schema.valid('option', 'stackup'):
        sc_stackup = schema.get('option', 'stackup')
    else:
        sc_stackup = schema.get('pdk', sc_pdk, 'stackup')[0]
    sc_mainlib = schema.get('asic', 'logiclib', step=sc_step, index=sc_index)[0]
    sc_libtype = schema.get('library', sc_mainlib, 'asic', 'libarch', step=sc_step, index=sc_index)

    sc_libs = []
    if 'logiclib' in schema.getkeys('asic'):
        sc_libs.extend(schema.get('asic', 'logiclib', step=sc_step, index=sc_index))
    if 'macrolib' in schema.getkeys('asic'):
        sc_libs.extend(schema.get('asic', 'macrolib', step=sc_step, index=sc_index))

    local_files = {
        'lyt': f'inputs/{design}.lyt',
        'lyp': f'inputs/{design}.lyp'
    }

    tech = pya.Technology.create_technology('sc_tech')
    # Load technology file
    tech_file = None
    if os.path.exists(local_files['lyt']):
        tech_file = local_files['lyt']
    elif schema.valid('pdk', sc_pdk, 'layermap', 'klayout', 'def', 'klayout', sc_stackup):
        tech_file = schema.get('pdk', sc_pdk, 'layermap', 'klayout', 'def', 'klayout', sc_stackup)
        if tech_file:
            tech_file = tech_file[0]

    if tech_file:
        print(f"[INFO] Loading technology file: {tech_file}")
        tech.load(tech_file)
    else:
        tech.name = f'{sc_pdk} for {sc_stackup}'
        tech.description = f'{", ".join(sc_libs)}'

    if schema.valid('pdk', sc_pdk, 'var', 'klayout', 'units', sc_stackup):
        units = float(schema.get('pdk', sc_pdk, 'var', 'klayout', 'units', sc_stackup)[0])
        tech.dbu = units
    print(f"[INFO] Technology database units are: {tech.dbu}um")

    lefs = []

    foundry_lef = schema.get('pdk', sc_pdk, 'aprtech', 'klayout', sc_stackup, sc_libtype, 'lef')
    if foundry_lef:
        foundry_lef = foundry_lef[0]
        lefs.append(foundry_lef)
    else:
        foundry_lef = None

    for lib in sc_libs:
        lefs.extend(schema.get('library', lib, 'output', sc_stackup, 'lef',
                               step=sc_step, index=sc_index))

    layoutOptions = tech.load_layout_options

    layoutOptions.lefdef_config.macro_resolution_mode = 1
    layoutOptions.lefdef_config.via_cellname_prefix = "VIA_"
    pathed_files = set()
    for lef_file in layoutOptions.lefdef_config.lef_files:
        if foundry_lef and not os.path.isabs(lef_file):
            lef_file = os.path.join(os.path.dirname(foundry_lef), lef_file)
        pathed_files.add(os.path.abspath(lef_file))

    for lef in lefs:
        pathed_files.add(os.path.abspath(lef))

    layoutOptions.lefdef_config.lef_files = list(pathed_files)
    layoutOptions.lefdef_config.read_lef_with_def = False

    for lef_file in layoutOptions.lefdef_config.lef_files:
        print(f"[INFO] LEF file: {lef_file}")

    # Set layer properties
    layer_properties = tech.layer_properties_file
    if layer_properties:
        layer_properties = layer_properties[0]
        if not os.path.isabs(layer_properties):
            layer_properties = os.path.abspath(os.path.join(os.path.dirname(tech_file),
                                                            layer_properties))
    if os.path.exists(local_files['lyp']):
        layer_properties = os.path.abspath(local_files['lyp'])
    elif schema.valid('pdk', sc_pdk, 'display', 'klayout', sc_stackup):
        pdk_layer_props = schema.get('pdk', sc_pdk, 'display', 'klayout', sc_stackup)
        if pdk_layer_props:
            layer_properties = pdk_layer_props[0]

    if layer_properties and os.path.exists(layer_properties):
        tech.layer_properties_file = layer_properties
        print(f"[INFO] Layer properties: {layer_properties}")

    # Set layer map
    map_file = layoutOptions.lefdef_config.map_file
    if map_file:
        map_file = map_file[0]
        if not os.path.isabs(map_file):
            map_file = os.path.abspath(os.path.join(os.path.dirname(tech_file),
                                                    map_file))
    for s in get_streams(schema):
        if schema.valid('pdk', sc_pdk, 'layermap', 'klayout', 'def', s, sc_stackup):
            map_file = schema.get('pdk', sc_pdk, 'layermap', 'klayout', 'def', s, sc_stackup)
            if map_file:
                map_file = map_file[0]
                break

    if map_file and os.path.exists(map_file):
        layoutOptions.lefdef_config.map_file = map_file
        print(f"[INFO] Layer map: {map_file}")

    tech.load_layout_options = layoutOptions

    return tech


def save_technology(design, tech):
    tech.default_base_path = '.'
    tech.base_path = '.'

    if tech.layer_properties_file:
        layer_file = f'{design}.lyp'
        shutil.copyfile(tech.layer_properties_file,
                        f'outputs/{layer_file}')
        tech.layer_properties_file = layer_file

    tech.save(f'outputs/{design}.lyt')
