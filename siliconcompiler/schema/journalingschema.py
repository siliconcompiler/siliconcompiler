import copy
import types

from .baseschema import BaseSchema
from .baseschema import json


class JournalingSchema(BaseSchema):
    """
    This class provides the ability to record the schema transactions:
    :meth:`set`, :meth:`add`, :meth:`remove`, and :meth:`unset`.

    Args:
        schema (:class:`BaseSchema`): schema to track
        keyprefix (list of str): keypath to prefix on to recorded path
    """

    def __init__(self, schema, keyprefix=None):
        if not isinstance(schema, BaseSchema):
            raise TypeError(f"schema must be of BaseSchema type, not: {type(schema)}")
        if isinstance(schema, JournalingSchema):
            raise TypeError("schema must be of cannot be a JournalingSchema")

        self.__schema = schema

        journal_attrs = dir(self)

        # Transfer access to internal schema
        for param, value in self.__schema.__dict__.items():
            setattr(self, param, value)
        for param in dir(type(self.__schema)):
            if param in journal_attrs:
                continue
            method = getattr(type(self.__schema), param)
            if callable(method):
                setattr(self, param, types.MethodType(method, self))

        if not keyprefix:
            self.__keyprefix = tuple()
        else:
            self.__keyprefix = tuple(keyprefix)

        self.__record_types = set()
        self.stop_journal()

        self.__parent = self

    @classmethod
    def from_manifest(cls, filepath=None, cfg=None):
        raise RuntimeError("Journal cannot be generated from manifest")

    def get(self, *keypath, field='value', step=None, index=None):
        get_ret = super().get(*keypath, field=field, step=step, index=index)
        self.__record_journal("get", keypath, field=field, step=step, index=index)
        if field == 'schema':
            child = JournalingSchema(get_ret, keyprefix=[*self.__keyprefix, *keypath])
            child.__parent = self.__parent
            return child

        return get_ret

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

        self.__schema._from_dict(manifest, keypath, version=version)

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

    def is_journaling(self):
        """
        Returns true if the schema is currently setup for journaling
        """
        return self.__journal is not None

    def get_journaling_types(self):
        """
        Returns the current schema accesses that are being recorded
        """

        return self.__record_types.copy()

    def add_journaling_type(self, value):
        """
        Adds a new access type to the journal record.

        Args:
            value (str): access type
        """

        if value not in ("set", "add", "remove", "unset", "get"):
            raise ValueError(f"{value} is not a valid type")

        return self.__record_types.add(value)

    def remove_journaling_type(self, value):
        """
        Removes a new access type to the journal record.

        Args:
            value (str): access type
        """

        try:
            self.__record_types.remove(value)
        except KeyError:
            pass

    def get_base_schema(self):
        """
        Returns the base schema
        """

        return self.__schema

    def __record_journal(self, record_type, key, value=None, field=None, step=None, index=None):
        '''
        Record the schema transaction
        '''

        if self.__parent.__journal is None:
            return

        if record_type not in self.__parent.__record_types:
            return

        self.__parent.__journal.append({
            "type": record_type,
            "key": tuple([*self.__keyprefix, *key]),
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
        self.add_journaling_type("set")
        self.add_journaling_type("add")
        self.add_journaling_type("remove")
        self.add_journaling_type("unset")

    def stop_journal(self):
        '''
        Stop journaling the schema transactions
        '''
        self.__journal = None
        self.__record_types.clear()

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

        if journal is None:
            return

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
            elif record_type == 'get':
                continue
            else:
                raise ValueError(f'Unknown record type {record_type}')
