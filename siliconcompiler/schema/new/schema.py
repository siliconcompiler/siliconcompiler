# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

import copy
import json

from siliconcompiler.schema.new.baseschema import BaseSchema
from siliconcompiler.schema.new.editableschema import EditableSchema
from siliconcompiler.schema.new.safeschema import SafeSchema
from siliconcompiler.schema.new.parameter import Parameter

from siliconcompiler.schema.new.schema_cfg import schema_cfg


class Schema(BaseSchema):
    def __init__(self):
        super().__init__()

        self.__history = {}

        schema_cfg(self)

        schema = EditableSchema(self)
        schema.add("library", "default", BaseSchema())

    def _from_dict(self, manifest, keypath, version=None):
        # find schema version
        schema_version = manifest.get("schemaversion", None)
        if not version and schema_version:
            param = Parameter.from_dict(schema_version, ["schemaversion"], None)
            version = param.get()

        current_verison = self.get("schemaversion")
        if current_verison != version:
            self.logger.warning(f"Mismatch in schema versions: {current_verison} != {version}")

        # Handle history special
        del manifest["history"]

        super()._from_dict(manifest, keypath, version=version)

    def getdict(self, *keypath, include_default=True):
        if keypath:
            # Handle history special
            if keypath[0] == "history":
                return []
            return super().getdict(*keypath, include_default=include_default)

        manifest = super().getdict(include_default=include_default)

        # Handle history special
        manifest["history"] = {}
        for name, obj in self.__history.items():
            manifest["history"][name] = obj.getdict(include_default=include_default)

        return manifest


class SchemaTmp(Schema):
    # TMP until cleanup
    GLOBAL_KEY = Parameter.GLOBAL_KEY

    def __init__(self, logger=None):
        super().__init__()

        self._stop_journal()

    def set(self, *args, field='value', clobber=True, step=None, index=None):
        if super().set(*args, field=field, clobber=clobber, step=step, index=index):
            *keypath, value = args
            self.__record_journal("set", keypath, value=value, field=field, step=step, index=index)
            return True
        return False

    def add(self, *args, field='value', step=None, index=None):
        if super().add(*args, field=field, step=step, index=index):
            *keypath, value = args
            self.__record_journal("add", keypath, value=value, field=field, step=step, index=index)
            return True
        return False

    def unset(self, *keypath, step=None, index=None):
        self.__record_journal("unset", keypath, step=step, index=index)
        super().unset(*keypath, step=step, index=index)

    def remove(self, *keypath):
        self.__record_journal("remove", keypath)
        super().remove(*keypath)

    # TMP needed until clean
    def __record_journal(self, record_type, key, value=None, field=None, step=None, index=None):
        '''
        Record the schema transaction
        '''
        if self.__journal is None:
            return

        self.__journal.append({
            "type": record_type,
            "key": key,
            "value": value,
            "field": field,
            "step": step,
            "index": index
        })

    # TMP needed until clean
    def _import_group(self, group, name, obj):
        group_obj = self._BaseSchema__search(group, require_leaf=False)
        group_obj._BaseSchema__manifest[name] = obj

    # TMP needed until clean
    def is_empty(self, *keypath):
        return self.get(*keypath, field=None).is_empty()

    # TMP needed until clean
    def has_field(self, *args):
        *keypath, field = args
        return self.get(*keypath, field=field) is not None

    # TMP needed until clean
    def _getvals(self, *keypath):
        return self.get(*keypath, field=None).getvalues()

    # TMP needed until clean
    def _start_journal(self):
        '''
        Start journaling the schema transactions
        '''
        self.__journal = []

    # TMP needed until clean
    def _stop_journal(self):
        '''
        Stop journaling the schema transactions
        '''
        self.__journal = None

    # TMP needed until clean
    def read_journal(self, filename):
        '''
        Reads a manifest and replays the journal
        '''

        with open(filename) as f:
            data = json.load(f)

        self._import_journal(self.from_manifest(cfg=data))

    # TMP needed until clean
    def _import_journal(self, schema):
        '''
        Import the journaled transactions from a different schema
        '''
        if not schema.__journal:
            return

        for action in schema.__journal:
            record_type = action['type']
            keypath = action['key']
            value = action['value']
            field = action['field']
            step = action['step']
            index = action['index']
            try:
                if record_type == 'set':
                    self.set(*keypath, value, field=field, step=step, index=index)
                elif record_type == 'add':
                    self.add(*keypath, value, field=field, step=step, index=index)
                elif record_type == 'unset':
                    self.unset(*keypath, step=step, index=index)
                elif record_type == 'remove':
                    self.remove(*keypath)
                else:
                    raise ValueError(f'Unknown record type {record_type}')
            except Exception as e:
                self.logger.error(f'Exception: {e}')

    # TMP needed until clean
    def _start_record_access(self):
        pass

    # TMP needed until clean
    def _do_record_access(self):
        pass

    # TMP needed until clean
    def _stop_record_access(self):
        pass

    def _from_dict(self, manifest, keypath, version=None):
        if "__journal__" in manifest:
            self.__journal = manifest["__journal__"]
            del manifest["__journal__"]

        super()._from_dict(manifest, keypath, version=version)

    def getdict(self, *keypath, include_default=True):
        manifest = super().getdict(*keypath, include_default=include_default)

        if self.__journal:
            manifest["__journal__"] = copy.deepcopy(self.__journal)

        return manifest

    # TMP needed until clean
    def write_json(self, fout):
        json.dump(self.getdict(), fout, indent=2)

    def write_tcl(self, fout, prefix="", step=None, index=None, template=None):
        from siliconcompiler.schema.new.parameter import escape_val_tcl
        import os.path

        tcl_set_cmds = []
        for key in self.allkeys():
            # print out all non default values
            if 'default' in key:
                continue

            param = self.get(*key, field=None)

            # create a TCL dict
            keystr = ' '.join([escape_val_tcl(keypart, 'str') for keypart in key])

            valstr = param.gettcl(step=step, index=index)
            if valstr is None:
                continue

            # Ensure empty values get something
            if valstr == '':
                valstr = '{}'

            tcl_set_cmds.append(f"{prefix} {keystr} {valstr}")

        if template:
            fout.write(template.render(manifest_dict='\n'.join(tcl_set_cmds),
                                       scroot=os.path.abspath(
                                              os.path.join(os.path.dirname(__file__), '..')),
                                       record_access=self._do_record_access(),
                                       record_access_id="123456"))
        else:
            for cmd in tcl_set_cmds:
                fout.write(cmd + '\n')
            fout.write('\n')


if __name__ == "__main__":
    schema = Schema()
    schema.set("pdk", "sky", "node", "5")
    schema.write_manifest("test.json")

    # safe = SafeSchema.from_manifest(filepath="test.json")
    safe = SafeSchema.from_manifest(cfg=schema.getdict())
    # safe.unlock()
    # safe.set('option', 'var', 'blah', 'blah')
    # safe.lock()
    # safe.set('option', 'var', 'blah', 'blah')
    safe.write_manifest("test2.json")
