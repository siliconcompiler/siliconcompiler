import copy
import json


class Journal:
    """
    This class provides the ability to record the schema transactions:
    :meth:`BaseSchema.set`, :meth:`BaseSchema.add`, :meth:`BaseSchema.remove`,
    :meth:`BaseSchema.unset`, and :meth:`BaseSchema.get`.

    Args:
        keyprefix (list of str): keypath to prefix on to recorded path
    """

    def __init__(self, keyprefix=None):
        if not keyprefix:
            self.__keyprefix = tuple()
        else:
            self.__keyprefix = tuple(keyprefix)

        self.__parent = self

        self.__record_types = set()
        self.stop()

    @property
    def keypath(self):
        '''
        Returns the reference key path for this journal
        '''

        return self.__keyprefix

    def get_child(self, *keypath):
        '''
        Get a child journal based on a new keypath

        Args:
            keypath (list of str): keypath to prefix on to recorded path
        '''

        child = Journal(keyprefix=[*self.__keyprefix, *keypath])
        child.__parent = self.__parent
        return child

    def from_dict(self, manifest):
        '''
        Import a journal from a manifest dictionary

        Args:
            manifest (dict): Manifest to decode.
        '''

        self.__journal = manifest

    def get(self):
        """
        Returns a copy of the current journal
        """

        return copy.deepcopy(self.__parent.__journal)

    def has_journaling(self):
        """
        Returns true if the schema is currently setup and is the root of the journal and has data
        """
        return self is self.__parent and bool(self.__journal)

    def is_journaling(self):
        """
        Returns true if the schema is currently setup for journaling
        """
        return self.__parent.__journal is not None

    def get_types(self):
        """
        Returns the current schema accesses that are being recorded
        """

        return self.__parent.__record_types.copy()

    def add_type(self, value):
        """
        Adds a new access type to the journal record.

        Args:
            value (str): access type
        """

        if value not in ("set", "add", "remove", "unset", "get"):
            raise ValueError(f"{value} is not a valid type")

        return self.__parent.__record_types.add(value)

    def remove_type(self, value):
        """
        Removes a new access type to the journal record.

        Args:
            value (str): access type
        """

        try:
            self.__parent.__record_types.remove(value)
        except KeyError:
            pass

    def record(self, record_type, key, value=None, field=None, step=None, index=None):
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

    def start(self):
        '''
        Start journaling the schema transactions
        '''
        self.__parent.__journal = []
        self.add_type("set")
        self.add_type("add")
        self.add_type("remove")
        self.add_type("unset")

    def stop(self):
        '''
        Stop journaling the schema transactions
        '''
        self.__parent.__journal = None
        self.__parent.__record_types.clear()

    @staticmethod
    def replay_file(schema, filepath):
        '''
        Replay a journal into a schema from a manifest

        Args:
            schema (:class:`BaseSchema`): schema to replay transactions to
            filepath (path): path to manifest
        '''
        with open(filepath, "r") as fid:
            data = json.load(fid)
        if "__journal__" not in data:
            return

        journal = Journal()
        journal.from_dict(data["__journal__"])
        journal.replay(schema)

    def replay(self, schema):
        '''
        Replay journal into a schema

        Args:
            schema (:class:`BaseSchema`): schema to replay transactions to
        '''

        from .baseschema import BaseSchema
        if not isinstance(schema, BaseSchema):
            raise TypeError(f"schema must be a BaseSchema, not {type(schema)}")

        if not self.__parent.__journal:
            return

        for action in self.__parent.__journal:
            record_type = action['type']
            keypath = action['key']
            value = action['value']
            field = action['field']
            step = action['step']
            index = action['index']
            if record_type == 'set':
                schema.set(*keypath, value, field=field, step=step, index=index)
            elif record_type == 'add':
                schema.add(*keypath, value, field=field, step=step, index=index)
            elif record_type == 'unset':
                schema.unset(*keypath, step=step, index=index)
            elif record_type == 'remove':
                schema.remove(*keypath)
            elif record_type == 'get':
                continue
            else:
                raise ValueError(f'Unknown record type {record_type}')

    @staticmethod
    def access(schema):
        '''
        Access a journal from a schema

        Args:
            schema (:class:`BaseSchema`): schema to replay transactions to access journal
        '''
        from .baseschema import BaseSchema
        if isinstance(schema, BaseSchema):
            return schema._BaseSchema__journal

        raise TypeError(f"schema must be a BaseSchema, not {type(schema)}")
