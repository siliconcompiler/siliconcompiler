import siliconcompiler
import json

chip = siliconcompiler.Chip()

chip.writecfg("sc_old.json")

#Create cfg
cfg = {}
cfg['extension'] = {
    'switch': '-extension',
    'type': 'str',
    'lock': 'false',
    'requirement': 'optional',
    'defvalue': None,
    'short_help': 'A user extension',
    'param_help': "extension <str>",
    'example': ["cli: -extension secret",
                "api: chip.add('extension', 'secret')"],
    'help': """
    A secret extension
    """
}

#dump file
with open("extend.json", 'w') as f:
    f.write(json.dumps(cfg, indent=4))
chip.extend("extend.json")
chip.writecfg("sc_new.json")

    
