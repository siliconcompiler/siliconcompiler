import argparse
import json
import os


def main():
    option_parser = argparse.ArgumentParser()
    # Command-line options
    option_parser.add_argument(
        "part_name",
        help="specify part number to prep")

    options = option_parser.parse_args()
    part_name = options.part_name

    pin_constraints = generate_mapped_constraints(part_name)

    write_json_constraints(
        pin_constraints,
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     f"pin_constraints_{part_name}.pcf"))


def generate_mapped_constraints(part_name):

    pin_constraints = {}

    if (part_name == 'example_arch_X014Y014'):

        for i in range(8):
            pin_constraints[f'a[{i}]'] = {
                "direction": "input",
                "pin": f'gpio_in_left[{i}]'
            }

        for i in range(8):
            pin_constraints[f'b[{i}]'] = {
                "direction": "input",
                "pin": f'gpio_in_right[{i}]'
            }

        for i in range(9):
            pin_constraints[f'y[{i}]'] = {
                "direction": "output",
                "pin": f'gpio_out_bottom[{i}]'
            }

    else:
        print(f"ERROR: unsupported part name {part_name}")

    return pin_constraints


def write_json_constraints(constraints, filename):

    with (open(filename, 'w')) as json_file:
        json_file.write(json.dumps(constraints, indent=2))
        json_file.write('\n')
        json_file.close()


if __name__ == "__main__":
    main()
