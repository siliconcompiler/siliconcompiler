import siliconcompiler
import json

chip = siliconcompiler.Chip()


#Create new config entry
cfg = {}
cfg['acme'] = {}
cfg['acme']['extension'] = {
    'switch': '-extension',
    'type': 'str',
    'lock': 'false',
    'requirement': 'optional',
    'defvalue': None,
    'value': None,
    'short_help': 'A user extension',
    'param_help': "extension <str>",
    'example': ["cli: -extension secret",
                "api: chip.add('extension', 'secret')"],
    'help': """
    A secret extension
    """
}

#dump into file
with open("extend.json", 'w') as f:
    f.write(json.dumps(cfg, indent=4))

#compare before and after
chip.writecfg("old.json", prune=False)
chip.extend("extend.json")
chip.writecfg("new.json", prune=False)
