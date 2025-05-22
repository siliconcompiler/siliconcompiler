from xml.etree import ElementTree
import xml.dom.minidom


def generate_vpr_constraints_xml_file(pin_map, filename):

    constraints_xml = generate_vpr_constraints_xml(pin_map)
    write_vpr_constraints_xml_file(constraints_xml, filename)


def generate_vpr_constraints_xml(pin_map):

    constraints_xml = ElementTree.Element("vpr_constraints")

    # Generate partition list section
    partition_list = generate_partition_list_xml(pin_map)

    constraints_xml.append(partition_list)

    return constraints_xml


def generate_partition_list_xml(pin_map):

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

    partition = ElementTree.Element("partition")

    partition_name = generate_partition_name(pin)
    partition.set("name", partition_name)

    atom_xml = generate_add_atom_xml(pin)
    partition.append(atom_xml)

    x_low, x_high, y_low, y_high, subtile = generate_region_from_pin(pin_region)
    region_xml = generate_add_region_xml(x_low, x_high, y_low, y_high, subtile)
    partition.append(region_xml)

    return partition


def generate_region_from_pin(pin_region):

    # ***ASSUMPTION:  Pin region is a 3-element tuple
    #                 containing (X,Y,subtile) coordinates

    # TODO figure out a scheme that supports VPR's notion
    # of specifying a region size of > 1x1
    x_low = int(pin_region[0])
    x_high = int(pin_region[0])
    y_low = int(pin_region[1])
    y_high = int(pin_region[1])
    subtile = int(pin_region[2])
    return x_low, x_high, y_low, y_high, subtile


def generate_partition_name(pin):

    partition_name = pin
    partition_name = partition_name.replace('[', '_')
    partition_name = partition_name.replace(']', '')
    partition_name = "part_" + partition_name

    return partition_name


def generate_add_atom_xml(pin_name):

    atom_xml = ElementTree.Element("add_atom")

    atom_xml.set("name_pattern", str(pin_name))

    return atom_xml


def generate_add_region_xml(x_low, x_high, y_low, y_high, subtile):

    region_xml = ElementTree.Element("add_region")

    region_xml.set("x_low", str(x_low))
    region_xml.set("y_low", str(y_low))
    region_xml.set("x_high", str(x_high))
    region_xml.set("y_high", str(y_high))
    region_xml.set("subtile", str(subtile))

    return region_xml


def write_vpr_constraints_xml_file(constraints: ElementTree.Element, filename: str):

    dom = xml.dom.minidom.parseString(ElementTree.tostring(constraints))
    xml_string = dom.toprettyxml()

    with open(filename, 'w') as xfile:
        xfile.write(str(xml_string))
