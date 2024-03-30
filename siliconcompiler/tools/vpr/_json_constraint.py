import argparse
import json

from _xml_constraint import generate_vpr_constraints_xml
from _xml_constraint import write_vpr_constraints_xml_file


def main():

    option_parser = argparse.ArgumentParser()
    option_parser.add_argument("-constraints_map",
                               help="architecture-specific mapping of constraint pins "
                                    "to FPGA core pins")
    option_parser.add_argument("json_constraints",
                               help="architecture-independent constraints file")
    option_parser.add_argument("constraints_file_out",
                               help="constraints XML file name")

    options = option_parser.parse_args()

    json_constraints_file = options.json_constraints
    constraints_map_file = options.constraints_map
    constraints_file_out = options.constraints_file_out

    json_generic_constraints = load_json_constraints(json_constraints_file)
    if (constraints_map_file):
        constraints_map = load_constraints_map(constraints_map_file)
    else:
        constraints_map = {}

    mapped_constraints = map_constraints(json_generic_constraints,
                                         constraints_map)

    constraints_xml = generate_vpr_constraints_xml(mapped_constraints)
    write_vpr_constraints_xml_file(constraints_xml, constraints_file_out)


def load_json_constraints(json_constraints_file):

    json_generic_constraints = {}
    with (open(json_constraints_file, "r")) as json_constraints_data:
        json_generic_constraints = json.loads(json_constraints_data.read())

    return json_generic_constraints


def load_constraints_map(constraints_map_file):

    constraints_map = {}
    with (open(constraints_map_file, "r")) as constraints_map_data:
        constraints_map = json.loads(constraints_map_data.read())

    return constraints_map


def map_constraints(json_generic_constraints,
                    constraints_map):

    design_constraints = {}

    # If no constraints map is provided pass the constraints directly
    if (len(constraints_map) == 0):

        for design_pin in json_generic_constraints:
            design_constraints[design_pin] = json_generic_constraints[design_pin]['pin']

    # Otherwise use the constraints map to remap the constraints to the correct
    # internal FPGA core pin:
    else:
        for design_pin in json_generic_constraints:

            design_pin_assignment = json_generic_constraints[design_pin]['pin']

            if (design_pin_assignment in constraints_map):
                # Convert the dictionary entries in the constraints map into a tuple:
                design_pin_constraint_assignment = (
                    constraints_map[design_pin_assignment]['x'],
                    constraints_map[design_pin_assignment]['y'],
                    constraints_map[design_pin_assignment]['subtile'])

            else:
                design_pin_constraint_assignment = (0, 0, 0)

            design_constraints[design_pin] = design_pin_constraint_assignment

    return design_constraints


if __name__ == "__main__":
    main()
