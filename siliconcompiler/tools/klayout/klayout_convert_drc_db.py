# KLayout script to export an OpenROAD marker DB from a DRC db
#
# Based on:
# https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/master/flow/util/convertDrc.py

import pya
import glob
import json
import os
import sys


def convert_drc(view, path):
    rdb_id = view.create_rdb(os.path.basename(path))
    rdb = view.rdb(rdb_id)
    print(f"[INFO] reading {path}")
    rdb.load(path)

    source = os.path.abspath(path)

    ordb = {
        "source": source,
        "description": "KLayout DRC conversion",
        "category": {}
    }

    for category in rdb.each_category():
        if category.num_items() == 0:
            # ignore categories with no data
            continue

        ordb_category = {
            "description": category.description,
            "source": source,
            "violations": []
        }
        ordb["category"][category.name()] = ordb_category

        for item in rdb.each_item_per_category(category.rdb_id()):
            violation = {
                "visited": item.is_visited(),
                "visible": True,
                "waived": "waived" in item.tags_str
            }

            ordb_category["violations"].append(violation)

            shapes = []
            violation["shape"] = shapes

            text = []

            for value in item.each_value():
                if value.is_box():
                    shapes.append({
                        "type": "box",
                        "points": [{
                            "x": value.box().left,
                            "y": value.box().bottom
                        }, {
                            "x": value.box().right,
                            "y": value.box().top
                        }]
                    })
                elif value.is_edge():
                    shapes.append({
                        "type": "line",
                        "points": [{
                            "x": value.edge().p1.x,
                            "y": value.edge().p1.y
                        }, {
                            "x": value.edge().p2.x,
                            "y": value.edge().p2.y
                        }]
                    })
                elif value.is_edge_pair():
                    edge1 = value.edge_pair().first
                    edge2 = value.edge_pair().second

                    shapes.append({
                        "type": "line",
                        "points": [{
                            "x": edge1.p1.x,
                            "y": edge1.p1.y
                        }, {
                            "x": edge1.p2.x,
                            "y": edge1.p2.y
                        }]
                    })
                    shapes.append({
                        "type": "line",
                        "points": [{
                            "x": edge2.p1.x,
                            "y": edge2.p1.y
                        }, {
                            "x": edge2.p2.x,
                            "y": edge2.p2.y
                        }]
                    })
                elif value.is_polygon():
                    points = []
                    for edge in value.polygon().each_edge():
                        points.append({
                            "x": edge.p1.x,
                            "y": edge.p1.y
                        })
                    points.append({
                        "x": edge.p2.x,
                        "y": edge.p2.y
                    })
                    shapes.append({
                        "type": "polygon",
                        "points": points
                    })
                elif value.is_path():
                    points = []
                    for edge in value.path().polygon().each_edge():
                        points.append({
                            "x": edge.p1.x,
                            "y": edge.p1.y
                        })
                    points.append({
                        "x": edge.p2.x,
                        "y": edge.p2.y
                    })
                    shapes.append({
                        "type": "polygon",
                        "points": points
                    })
                elif value.is_text():
                    text.append(value.text())
                elif value.is_string():
                    text.append(value.string())
                else:
                    print("[WARN] Unknown violation shape:", value)

            comment = ""
            if hasattr(item, 'comment'):
                comment = item.comment
            if text:
                if comment:
                    comment += ": "
                comment += ", ".join(text)

            if comment:
                violation["comment"] = comment

    return ordb


def main():
    # SC_ROOT provided by CLI
    sys.path.append(SC_KLAYOUT_ROOT)  # noqa: F821

    from klayout_utils import get_schema

    schema = get_schema(manifest='sc_manifest.json')

    design = schema.get('design')

    app = pya.Application.instance()
    win = app.main_window()

    # Create a dummy view to use for loading
    cell_view = win.create_layout(0)
    layout_view = cell_view.view()

    ordb = {}
    for file in glob.glob(f'inputs/{design}*.lyrdb') + glob.glob('inputs/{design}*.ascii'):
        name = os.path.basename(file)

        ordb[name] = convert_drc(layout_view, file)

    with open(f"outputs/{design}.json", "w") as outfile:
        json.dump(
            ordb,
            outfile,
            indent=2)


if __name__ == '__main__':
    main()
