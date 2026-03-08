import json


def load_json_constraints(json_constraints_file):
    """
    Loads JSON constraints from a file.

    Args:
        json_constraints_file (str): Path to the JSON constraints file.

    Returns:
        dict: The loaded JSON data.
    """
    with open(json_constraints_file, "r") as json_constraints_data:
        return json.load(json_constraints_data)


def load_constraints_map(constraints_map_file):
    """
    Loads the constraints map from a file.

    Args:
        constraints_map_file (str): Path to the constraints map file.

    Returns:
        dict: The loaded constraints map.
    """
    with open(constraints_map_file, "r") as constraints_map_data:
        return json.load(constraints_map_data)


def map_constraints(logger,
                    json_generic_constraints,
                    constraints_map):
    """
    Maps generic JSON constraints to VPR-specific constraints using a map.

    Args:
        logger (logging.Logger): Logger object for error reporting.
        json_generic_constraints (dict): The generic constraints loaded from JSON.
        constraints_map (dict): The constraints map loaded from JSON.

    Returns:
        tuple: A tuple containing the design constraints dictionary and the error count.
    """
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
            if json_generic_constraints[design_pin]['direction'] == "output":
                named_design_pin = f'out:{design_pin}'
            else:
                named_design_pin = design_pin

            design_pin_assignment = json_generic_constraints[design_pin]['pin']

            if design_pin_assignment in constraints_map:
                # Convert the dictionary entries in the constraints map into a tuple:
                design_pin_constraint_assignment = (
                    constraints_map[design_pin_assignment].get('x', None),
                    constraints_map[design_pin_assignment].get('y', None),
                    constraints_map[design_pin_assignment].get('subtile', None),
                    constraints_map[design_pin_assignment].get('block_type', None)
                )

                design_constraints[named_design_pin] = design_pin_constraint_assignment

            else:
                logger.error(f'Cannot map to pin {design_pin_assignment}')
                errors += 1

    return design_constraints, errors
