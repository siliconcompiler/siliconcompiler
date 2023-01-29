# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.

from .schema_cfg import schema_cfg
from .schema_obj import Schema

class PDKSchema(Schema):
    """
    Schema sub-class for storing PDK keys.

    This object is used to help construct a Chip object's configuration. In almost all cases,
    the base Schema class should be used instead of this.

    Attempts to set values outside of the top-level 'pdk' Schema key will cause errors,
    which should help us to keep liberty/tool/etc configurations out of our PDK setup modules.
    """

    def __init__(self, cfg=None, manifest=None):
        if cfg is not None and manifest is not None:
            raise ValueError('You may not specify both cfg and manifest')

        if cfg is not None:
            self.cfg = copy.deepcopy(cfg)
        elif manifest is not None:
            self.cfg = Schema._read_manifest(manifest)
        else:
            self.cfg = schema_cfg()

        # Only use PDK keys, and some minor bookkeeping.
        # Convert to 'list' to prefetch keys, and avoid modifying the dict during iteration.
        for k in list(self.cfg.keys()):
            if not k in ('pdk', 'schemaversion'):
                self.cfg.pop(k)

    ##########################################################################
    def record_history(self):
        ''' Override 'record_history' method, since Schema subclasses are only used for imports.
        '''
        pass

    ###########################################################################
    def history(self, job):
        ''' Override 'record_history' method, since Schema subclasses are only used for imports.
        '''
        return None

    ###########################################################################
    def copy(self):
        '''Returns deep copy of PDKSchema object.'''
        return PDKSchema(cfg=self.cfg)
