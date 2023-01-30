# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.
import os
import sys

from siliconcompiler import _metadata
from siliconcompiler.core.schema_consumer import SchemaConsumer

class PDK(SchemaConsumer):
    """
    Object for configuring PDK-related information.

    This object is a 'sibling' of the Chip object, with a similar Schema and set/get/add/etc methods.
    Unlike the main Chip object, however, this PDK object can only modify schema parameters which are
    under the top-level 'pdk' key path.

    This is intended as a helper object for module authors, to ensure that the Chip objects can
    recognize PDK modules during the import process, and be assured that those modules have not set
    any build parameters outside of the PDK 'namespace'.
    """

    ###########################################################################
    def __init__(self, loglevel=None):
        # SchemaConsumer initialization
        super().__init__(loglevel)

        # version numbers
        self.scversion = _metadata.version

        # Only allow PDK Schema keys, and some minor bookkeeping like semver.
        # Convert to 'list' to prefetch keys, and avoid modifying the dict during iteration.
        for k in list(self.schema.cfg.keys()):
            if not k in ('pdk', 'schemaversion'):
                self.schema.cfg.pop(k)
