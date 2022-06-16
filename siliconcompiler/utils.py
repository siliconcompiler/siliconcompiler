import os
import shutil
import sys
import xml.etree.ElementTree as ET
import re
def copytree(src, dst, ignore=[], dirs_exist_ok=False, link=False):
    '''Simple implementation of shutil.copytree to give us a dirs_exist_ok
    option in Python < 3.8.

    If link is True, create hard links in dst pointing to files in src
    instead of copying them.
    '''
    os.makedirs(dst, exist_ok=dirs_exist_ok)

    for name in os.listdir(src):
        if name in ignore:
            continue

        srcfile = os.path.join(src, name)
        dstfile = os.path.join(dst, name)

        if os.path.isdir(srcfile):
            copytree(srcfile, dstfile, ignore=ignore, dirs_exist_ok=dirs_exist_ok)
        elif link:
            os.link(srcfile, dstfile)
        else:
            shutil.copy2(srcfile, dstfile)

def trim(docstring):
    '''Helper function for cleaning up indentation of docstring.

    This is important for properly parsing complex RST in our docs.

    Source:
    https://www.python.org/dev/peps/pep-0257/#handling-docstring-indentation'''
    if not docstring:
        return ''
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxsize
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxsize:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    # Return a single string:
    return '\n'.join(trimmed)


class PbPrimitive:
     
    def __init__ (self, name, blif_model):
        self.name = name
        self.blif_model = blif_model
        self.ports = []    
        
    def add_port(self, port):
        
        port_type = port.tag
        port_name = port.attrib['name']
        num_pins = port.attrib['num_pins']
        port_class = port.attrib.get('port_class')
        
        new_port = { 'port_type': port_type,
                     'port_name': port_name,
                     'num_pins': num_pins,
                     'port_class': port_class }
        
        self.ports.append(new_port)
        
    def find_port(self, port_name):
        print(port_name)
        for port in self.ports:
            if re.match(port_name, port['port_name']):
                return port
        return None
    
class Arch:
    
    def __init__(self, arch_file_name):
        self.arch_file = ET.parse(arch_file_name)
        self.complexblocklist = self.arch_file.find("complexblocklist")
        self.pb_primitives = []
        self.find_pb_primitives(self.complexblocklist)
    
    def find_pb_primitives(self, root):  
        for pb_type in root.iter('pb_type'):
            if "blif_model" in pb_type.attrib:
                self.add_pb_primitive(pb_type)
                
    def add_pb_primitive(self, pb_type):
        new_pb = PbPrimitive(pb_type.tag, pb_type.attrib["blif_model"])
        for port in pb_type.iter():
            if port.tag in ['input', 'output', 'clock']:
                new_pb.add_port(port)
        self.pb_primitives.append(new_pb)
        
    def find_max_lut_size(self):
        max_lut_size = 0
        for pb_type in self.pb_primitives:
            if pb_type.blif_model == ".names":
                in_port = pb_type.find_port("in")
                lut_size = in_port["num_pins"]
                max_lut_size = max(max_lut_size, int(lut_size))
                
        return max_lut_size
    
    def find_memory_addr_width(self):
        max_add_size = 0
        for pb_type in self.pb_primitives:
            if "port_ram" in pb_type.blif_model:
                add_port = pb_type.find_port("^addr")
                add_size = add_port["num_pins"]
                max_add_size = max(max_add_size, int(add_size))
                
        return max_add_size
 