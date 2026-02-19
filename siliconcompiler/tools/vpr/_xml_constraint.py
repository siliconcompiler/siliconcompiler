from xml.etree import ElementTree
import xml.dom.minidom


def generate_vpr_constraints_xml_file(pin_map, filename):
    """
    Generates a VPR constraints XML file from a pin map.

    Args:
        pin_map (dict): Dictionary mapping pin names to location tuples.
        filename (str): Output filename for the XML constraints.
    """
    write_vpr_constraints_xml_file(generate_vpr_constraints_xml(pin_map), filename)


def generate_vpr_constraints_xml(pin_map):
    """
    Generates the root XML element for VPR constraints.

    Args:
        pin_map (dict): Dictionary mapping pin names to location tuples.

    Returns:
        xml.etree.ElementTree.Element: The root 'vpr_constraints' element.
    """
    constraints_xml = ElementTree.Element("vpr_constraints")

    # Generate partition list section
    constraints_xml.append(generate_partition_list_xml(pin_map))

    return constraints_xml


def generate_partition_list_xml(pin_map):
    """
    Generates the partition list XML element.

    Args:
        pin_map (dict): Dictionary mapping pin names to location tuples.

    Returns:
        xml.etree.ElementTree.Element: The 'partition_list' element.
    """
    partition_list = ElementTree.Element("partition_list")

    # ***ASSUMPTION:  pin map is a dictionary of block names
    #                 and tuples, where the tuples specify the
    #                 (X,Y,subtile) locations that each block
    #                 is constrained to
    for pin, region in pin_map.items():
        cur_partition = generate_partition_xml(pin, region)
        partition_list.append(cur_partition)

    return partition_list


def generate_partition_xml(pin, pin_region):
    """
    Generates a partition XML element for a specific pin.

    Args:
        pin (str): The name of the pin/block.
        pin_region (tuple): A tuple containing (x, y, subtile, block_type).

    Returns:
        xml.etree.ElementTree.Element: The 'partition' element.
    """
    partition = ElementTree.Element("partition")

    partition_name = generate_partition_name(pin)
    partition.set("name", partition_name)

    partition.append(generate_add_atom_xml(pin))

    x_low, x_high, y_low, y_high, subtile, block_type = generate_region_from_pin(pin_region)

    if block_type:
        partition.append(generate_add_block_type_xml(block_type))

    partition.append(generate_add_region_xml(x_low, x_high, y_low, y_high, subtile))

    return partition


def generate_add_block_type_xml(block_name):
    """
    Generates an add_logical_block XML element.

    Args:
        block_name (str): The name pattern for the logical block.

    Returns:
        xml.etree.ElementTree.Element: The 'add_logical_block' element.
    """
    block_type_xml = ElementTree.Element("add_logical_block")

    block_type_xml.set("name_pattern", str(block_name))

    return block_type_xml


def generate_region_from_pin(pin_region):
    """
    Extracts region coordinates and info from a pin region tuple.

    Args:
        pin_region (tuple): A tuple containing (x, y, subtile, block_type).

    Returns:
        tuple: (x_low, x_high, y_low, y_high, subtile, block_type)
    """
    # ***ASSUMPTION:  Pin region is a 4-element tuple
    #                 containing (X,Y,subtile,block_type)

    # TODO figure out a scheme that supports VPR's notion
    # of specifying a region size of > 1x1
    x_low = int(pin_region[0])
    x_high = int(pin_region[0])
    y_low = int(pin_region[1])
    y_high = int(pin_region[1])
    subtile = int(pin_region[2])
    block_type = pin_region[3]
    return x_low, x_high, y_low, y_high, subtile, block_type


def generate_partition_name(pin):
    """
    Generates a sanitized partition name from a pin name.

    Args:
        pin (str): The original pin name.

    Returns:
        str: The sanitized partition name.
    """
    partition_name = pin
    partition_name = partition_name.replace('[', '_')
    partition_name = partition_name.replace(']', '')
    partition_name = "part_" + partition_name

    return partition_name


def generate_add_atom_xml(pin_name):
    """
    Generates an add_atom XML element.

    Args:
        pin_name (str): The name pattern for the atom.

    Returns:
        xml.etree.ElementTree.Element: The 'add_atom' element.
    """
    atom_xml = ElementTree.Element("add_atom")

    atom_xml.set("name_pattern", str(pin_name))

    return atom_xml


def generate_add_region_xml(x_low, x_high, y_low, y_high, subtile):
    """
    Generates an add_region XML element.

    Args:
        x_low (int): Minimum X coordinate.
        x_high (int): Maximum X coordinate.
        y_low (int): Minimum Y coordinate.
        y_high (int): Maximum Y coordinate.
        subtile (int): Subtile index.

    Returns:
        xml.etree.ElementTree.Element: The 'add_region' element.
    """
    region_xml = ElementTree.Element("add_region")

    region_xml.set("x_low", str(x_low))
    region_xml.set("y_low", str(y_low))
    region_xml.set("x_high", str(x_high))
    region_xml.set("y_high", str(y_high))
    region_xml.set("subtile", str(subtile))

    return region_xml


def write_vpr_constraints_xml_file(constraints: ElementTree.Element, filename: str):
    """
    Writes the VPR constraints XML tree to a file with pretty printing.

    Args:
        constraints (xml.etree.ElementTree.Element): The root XML element.
        filename (str): The output filename.
    """
    dom = xml.dom.minidom.parseString(ElementTree.tostring(constraints))
    with open(filename, 'w') as xfile:
        xfile.write(dom.toprettyxml())
