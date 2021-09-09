from ._leflib import parse as _parse

def parse(path):
    ''' Parses LEF file.

    Given a path to a LEF file, this function parses the file and returns a
    dictionary representing the contents of the LEF file. If there's an error
    while reading or parsing the file, this function returns None instead.

    Note that this function does not return all information contained in the
    LEF. The subset of information returned includes:

    * LEF version
    * Manufacturing grid
    * Units
    * Macro information

        * Size
        * Pins
        * Obstructions
    * Layer information

        * Type
        * Width
        * Direction
        * Offset
        * Pitch
    * Viarules

    The dictionary returned by this function is designed to mimic the structure
    of the LEF file as closely as possible, and this function does minimal
    legality checking. It looks like follows:

        .. code-block:: python

            {
                'version': 5.8,
                'manufacturinggrid': 0.05,
                'units': {
                    'capacitance': 10.0,
                    'current': 10000.0,
                    'database': 20000.0,
                    'frequency': 10.0,
                    'power': 10000.0,
                    'resistance': 10000.0,
                    'time': 100.0,
                    'voltage': 1000.0
                },
                'layers': {
                    'm1': {
                        'type': 'ROUTING',
                        'direction': 'HORIZONTAL',
                        'pitch': 1.8,
                        'width': 1.0
                    },
                    'v1': {
                        'type': 'CUT',
                    },
                    ...
                },
                'macros': {
                    '<name>': {
                        'pins': {
                            '<name>': {
                                'direction': 'input' | 'output' | 'output tristate' | 'inout' | 'feedthru',
                                'ports': [{
                                    'class': 'none' | 'core' | 'bump',
                                    'layer_geometries': [{
                                        'layer': 'm1',
                                        'exceptpgnet': True,
                                        'spacing': ...,
                                        'designrulewidth': ...,
                                        'width': width,
                                        'shapes': [
                                            {
                                                'rect': (0, 0, 5, 5),
                                                'mask': maskNum,
                                                'iterate': {
                                                    'num_x': numX,
                                                    'num_y': numY',
                                                    'space_x': spaceX,
                                                    'space_y': spaceY
                                                }
                                            },
                                            {
                                                'path': [pt, pt, ...],
                                                'mask': maskNum,
                                                'iterate': step_pattern
                                            },
                                            {
                                                'polygon': [pt, pt, ...],
                                                'mask': maskNum,
                                                'iterate': step_pattern
                                            }
                                        ],
                                        'via': {
                                            'pt': pt,
                                            'name': viaName,
                                            'iterate': step_pattern
                                        }
                                    }]
                                }]
                            }
                        }
                        'size': {
                            'width': 5,
                            'height': 8
                        }
                    }
                }
                'viarules': {
                    ...
                }
            }

    If some entry is not specified in the LEF, the corresponding key will not be
    present in the dictionary.

    Args:
        path (str): Path to LEF file to parse.
    '''

    return _parse(path)
