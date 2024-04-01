import json


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


def map_constraints(chip,
                    json_generic_constraints,
                    constraints_map):

    design_constraints = {}
    errors = 0

    # If no constraints map is provided pass the constraints directly
    if not constraints_map:

        for design_pin in json_generic_constraints:
            design_constraints[design_pin] = json_generic_constraints[design_pin]['pin']

    # Otherwise use the constraints map to remap the constraints to the correct
    # internal FPGA core pin:
    else:
        for design_pin in json_generic_constraints:

            # VPR has a quirk that it prepends "out:" to outputs to differentiate
            # the pin from any block name that may have inherited its instance name
            # from an output.  Compensate for that quirk here
            if (json_generic_constraints[design_pin]['direction'] == "output"):
                named_design_pin = f'out:{design_pin}'
            else:
                named_design_pin = design_pin

            design_pin_assignment = json_generic_constraints[design_pin]['pin']

            if (design_pin_assignment in constraints_map):
                # Convert the dictionary entries in the constraints map into a tuple:
                design_pin_constraint_assignment = (
                    constraints_map[design_pin_assignment]['x'],
                    constraints_map[design_pin_assignment]['y'],
                    constraints_map[design_pin_assignment]['subtile'])

                design_constraints[named_design_pin] = design_pin_constraint_assignment

            else:
                chip.logger.error(f'Cannot map to pin {design_pin_assignment}')
                errors += 1

    return design_constraints, errors
