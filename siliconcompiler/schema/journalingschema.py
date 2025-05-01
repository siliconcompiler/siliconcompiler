import copy

from .baseschema import BaseSchema
from .baseschema import json


class JournalingSchema(BaseSchema):
    """
    This class provides the ability to record the schema transactions:
    :meth:`set`, :meth:`add`, :meth:`remove`, and :meth:`unset`.

    Args:
        schema (:class:`BaseSchema`): schema to track
    """

    def __init__(self, schema):
        if not isinstance(schema, BaseSchema):
            raise TypeError(f"schema must be of BaseSchema type, not, {type(schema)}")

        self.__schema = schema

        # Transfer access to internal schema
        for param, value in self.__schema.__dict__.items():
            setattr(self, param, value)

        self.stop_journal()

    def get(self, *keypath, field='value', step=None, index=None):
        return super().get(*keypath, field=field, step=step, index=index)

    def set(self, *args, field='value', clobber=True, step=None, index=None):
        ret = super().set(*args, field=field, clobber=clobber, step=step, index=index)
        if ret:
            *keypath, value = args
            self.__record_journal("set", keypath, value=value, field=field, step=step, index=index)
        return ret

    def add(self, *args, field='value', step=None, index=None):
        ret = super().add(*args, field=field, step=step, index=index)
        if ret:
            *keypath, value = args
            self.__record_journal("add", keypath, value=value, field=field, step=step, index=index)
        return ret

    def remove(self, *keypath):
        self.__record_journal("remove", keypath)
        return super().remove(*keypath)

    def unset(self, *keypath, step=None, index=None):
        self.__record_journal("unset", keypath, step=step, index=index)
        return super().unset(*keypath, step=step, index=index)

    def _from_dict(self, manifest, keypath, version=None):
        if "__journal__" in manifest:
            self.__journal = manifest["__journal__"]
            del manifest["__journal__"]

        super()._from_dict(manifest, keypath, version=version)

    def getdict(self, *keypath, include_default=True):
        manifest = super().getdict(*keypath, include_default=include_default)

        if self.__journal:
            manifest["__journal__"] = self.get_journal()

        return manifest

    def get_journal(self):
        """
        Returns a copy of the current journal
        """

        return copy.deepcopy(self.__journal)

    def get_base_schema(self):
        """
        Returns the base schema
        """

        return self.__schema

    def __record_journal(self, record_type, key, value=None, field=None, step=None, index=None):
        '''
        Record the schema transaction
        '''
        if self.__journal is None:
            return

        self.__journal.append({
            "type": record_type,
            "key": tuple(key),
            "value": value,
            "field": field,
            "step": step,
            "index": index
        })

    def start_journal(self):
        '''
        Start journaling the schema transactions
        '''
        self.__journal = []

    def stop_journal(self):
        '''
        Stop journaling the schema transactions
        '''
        self.__journal = None

    def read_journal(self, filename):
        '''
        Reads a manifest and replays the journal
        '''

        with open(filename) as f:
            data = json.loads(f.read())

        self.import_journal(cfg=data)

    def import_journal(self, schema=None, cfg=None):
        '''
        Import the journaled transactions from a different schema.
        Only one argument is supported at a time.

        Args:
            schema (:class:`JournalingSchema`): schema to replay transactions from
            cfg (dict): dictionary to replay transactions from
        '''

        if schema and cfg:
            raise ValueError("only one argument is supported")

        journal = []
        if schema:
            if isinstance(schema, JournalingSchema):
                journal = schema.__journal
            else:
                raise TypeError(f"schema must be a JournalingSchema, not {type(schema)}")
        elif cfg and "__journal__" in cfg:
            journal = cfg["__journal__"]

        for action in journal:
            record_type = action['type']
            keypath = action['key']
            value = action['value']
            field = action['field']
            step = action['step']
            index = action['index']
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
