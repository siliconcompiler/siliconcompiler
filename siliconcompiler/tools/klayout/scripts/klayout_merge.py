import pya
import sys

import os.path


if __name__ == "__main__":
    # SC_ROOT provided by CLI
    sys.path.append(SC_KLAYOUT_ROOT)  # noqa: F821
    sys.path.append(SC_TOOLS_ROOT)  # noqa: F821
    sys.path.append(SC_ROOT)  # noqa: F821

    from klayout_utils import (
        technology,
        get_schema,
        generate_metrics
    )

    from klayout_operations import (
        read_layout,
        write_stream
    )

    schema = get_schema(manifest='sc_manifest.json')

    # Extract info from manifest
    sc_step = schema.get('arg', 'step')
    sc_index = schema.get('arg', 'index')
    sc_tool = 'klayout'
    sc_task = 'merge'

    design_name = schema.get('option', 'design')
    fileset = schema.get("option", "fileset")[0]
    design = schema.get("library", design_name, "fileset", fileset, "topmodule")

    ref_type, ref_source0, ref_source1 = schema.get("tool", sc_tool, "task", sc_task,
                                                    "var", "reference",
                                                    step=sc_step, index=sc_index)
    if ref_type == 'input':
        step, index = ref_source0, ref_source1
        input_file = os.path.join('inputs', f"{design}.{ref_source0}{ref_source1}.gds")
    else:
        input_file = schema.get("library", ref_source0, "fileset", ref_source1, "file", "gds")[0]

    merge_files = []
    for merge_type, merge_source0, merge_source1, prefix in \
            schema.get("tool", sc_tool, "task", sc_task, "var", "merge",
                       step=sc_step, index=sc_index):
        if merge_type == 'input':
            merge_file = os.path.join('inputs', f"{design}.{merge_source0}{merge_source1}.gds")
        else:
            merge_file = schema.get("library", merge_source0, "fileset", merge_source1,
                                    "file", "gds")[0]
        merge_files.append((prefix, merge_file))

    tech = technology(design, schema)
    base_layout = read_layout(input_file)
    top_cell = base_layout.top_cell()
    base_layout.technology_name = tech.name

    for prefix, merge_file in merge_files:
        print(f"[INFO] Merging file '{merge_file}' with prefix '{prefix}'")
        merge_layout = read_layout(merge_file)

        merge_top = merge_layout.top_cell()

        new_cell_name = f"{prefix}{merge_top.name}"
        if base_layout.cell(new_cell_name):
            print(f"[WARN] Cell '{new_cell_name}' already exists in base layout. Skipping.")
            continue
        print(f"[INFO] Adding cell '{merge_top.name}' as '{new_cell_name}'")
        new_cell = base_layout.create_cell(new_cell_name)
        new_cell.copy_tree(merge_top)
        cell_inst = pya.CellInstArray(new_cell.cell_index(), pya.Trans())
        top_cell.insert(cell_inst)

    write_stream(base_layout, f"outputs/{design}.gds", True)

    generate_metrics()
