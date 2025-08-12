import pytest
import re
import shutil
import os.path
from pathlib import Path

from siliconcompiler import SchematicSchema

def test_design_keys():
    golden_keys = set([
        ('schematic', 'hierchar'),
        ('schematic', 'buschar'),
        ('schematic', 'component', 'default', 'partname'),
        ('schematic', 'pin', 'default', 'direction'),
        ('schematic', 'net', 'default', 'connection')
    ])

    assert set(SchematicSchema("test").allkeys()) == golden_keys
