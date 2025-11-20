import pya
import json
import shutil
import os.path


def get_streams(schema):
    sc_step = schema.get('arg', 'step')
    sc_index = schema.get('arg', 'index')
    sc_flow = schema.get('option', 'flow')
    sc_task = schema.get('flowgraph', sc_flow, sc_step, sc_index, 'task')

    streams = ('gds', 'oas')
    if schema.valid('tool', 'klayout', 'task', sc_task, 'var', 'stream'):
        sc_stream = schema.get('tool', 'klayout', 'task', sc_task, 'var', 'stream',
                               step=sc_step, index=sc_index)
    else:
        sc_stream = streams[0]
    return [sc_stream, *[s for s in streams if s != sc_stream]]


def technology(design, schema):
    sc_libs = schema.get('asic', 'asiclib')

    local_files = {
        'lyt': f'inputs/{design}.lyt',
        'lyp': f'inputs/{design}.lyp'
    }

    sc_pdk = schema.get("asic", "pdk")

    tech = pya.Technology.create_technology('sc_tech')
    # Load technology file
    tech_file = None
    if os.path.exists(local_files['lyt']):
        tech_file = local_files['lyt']
    elif schema.valid('library', sc_pdk, 'pdk', 'layermapfileset', 'klayout', 'def', 'klayout'):
        for fileset in schema.get('library', sc_pdk, 'pdk',
                                  'layermapfileset', 'klayout', 'def', 'klayout'):
            if schema.valid('library', sc_pdk, "fileset", fileset, "file", "layermap"):
                tech_file = schema.get('library', sc_pdk, "fileset", fileset, "file", "layermap")
        if tech_file:
            tech_file = tech_file[0]

    if tech_file:
        print(f"[INFO] Loading technology file: {tech_file}")
        tech.load(tech_file)
    else:
        tech.name = sc_pdk
        tech.description = f'{", ".join(sc_libs)}'

    if schema.valid('library', sc_pdk, 'tool', 'klayout', 'units'):
        units = schema.get('library', sc_pdk, 'tool', 'klayout', 'units')
        if units is not None and units > 0:
            tech.dbu = units
    print(f"[INFO] Technology database units are: {tech.dbu}um")

    lefs = []

    foundry_lef = None
    if schema.valid('library', sc_pdk, "pdk", 'aprtechfileset', "klayout"):
        for fileset in schema.get('library', sc_pdk, "pdk", 'aprtechfileset', "klayout"):
            if schema.valid('library', sc_pdk, "fileset", fileset, "file", "lef"):
                foundry_lef = schema.get('library', sc_pdk, "fileset", fileset, "file", "lef")
    if foundry_lef:
        foundry_lef = foundry_lef[0]
        lefs.append(foundry_lef)
    else:
        foundry_lef = None

    for lib in sc_libs:
        if schema.valid('library', lib, "asic", "aprfileset"):
            for fileset in schema.get("library", lib, "asic", "aprfileset"):
                if schema.valid("library", lib, "fileset", fileset, "file", "lef"):
                    lefs.extend(schema.get("library", lib, "fileset", fileset, "file", "lef"))

    layout_options = tech.load_layout_options

    layout_options.lefdef_config.macro_resolution_mode = 1
    layout_options.lefdef_config.via_cellname_prefix = "VIA_"
    pathed_files = set()
    for lef_file in layout_options.lefdef_config.lef_files:
        if foundry_lef and not os.path.isabs(lef_file):
            lef_file = os.path.join(os.path.dirname(foundry_lef), lef_file)
        lef_file = os.path.abspath(lef_file)
        if os.path.isfile(lef_file):
            pathed_files.add(os.path.abspath(lef_file))

    for lef in lefs:
        pathed_files.add(os.path.abspath(lef))

    layout_options.lefdef_config.lef_files = list(pathed_files)
    layout_options.lefdef_config.read_lef_with_def = False
    layout_options.lefdef_config.dbu = tech.dbu

    layout_options.lefdef_config.produce_fills = True

    for lef_file in layout_options.lefdef_config.lef_files:
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
    elif schema.valid('library', sc_pdk, "pdk", 'displayfileset', 'klayout'):
        pdk_layer_props = None
        for fileset in schema.get('library', sc_pdk, "pdk", 'displayfileset', 'klayout'):
            if schema.valid("library", sc_pdk, "fileset", fileset, "file", "display"):
                pdk_layer_props = schema.get("library", sc_pdk, "fileset", fileset,
                                             "file", "display")
        if pdk_layer_props:
            layer_properties = pdk_layer_props[0]

    if layer_properties and os.path.exists(layer_properties):
        tech.layer_properties_file = layer_properties
        print(f"[INFO] Layer properties: {layer_properties}")

    # Set layer map
    map_file = layout_options.lefdef_config.map_file
    if map_file:
        map_file = map_file[0]
        if not os.path.isabs(map_file):
            map_file = os.path.abspath(os.path.join(os.path.dirname(tech_file),
                                                    map_file))
    for s in get_streams(schema):
        if schema.valid('library', sc_pdk, 'pdk', 'layermapfileset', 'klayout', 'def', s):
            for fileset in schema.get('library', sc_pdk, 'pdk', 'layermapfileset', 'klayout',
                                      'def', s):
                if schema.valid('library', sc_pdk, "fileset", fileset, "file", "layermap"):
                    map_file = schema.get('library', sc_pdk, "fileset", fileset, "file", "layermap")
                if map_file:
                    map_file = map_file[0]
                    break
        if map_file:
            break

    if map_file and os.path.exists(map_file):
        layout_options.lefdef_config.map_file = map_file
        print(f"[INFO] Layer map: {map_file}")

    tech.load_layout_options = layout_options

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


def get_write_options(filename, timestamps):
    write_options = pya.SaveLayoutOptions()
    write_options.gds2_write_timestamps = timestamps
    write_options.set_format_from_filename(filename)

    return write_options


def get_schema(manifest):
    from schema.safeschema import SafeSchema
    return SafeSchema.from_manifest(filepath=manifest)


def generate_metrics():
    metrics = {}

    main_window = pya.MainWindow.instance()
    if not main_window:
        return
    layout_view = main_window.current_view()
    if not layout_view:
        return
    cell_view = layout_view.active_cellview()
    if not cell_view:
        return
    cell = cell_view.cell
    if not cell:
        return

    metrics["area"] = cell.dbbox().area()

    with open('reports/metrics.json', 'w') as f:
        json.dump(metrics, f, indent=2)
