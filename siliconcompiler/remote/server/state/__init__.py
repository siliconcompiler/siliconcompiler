'''
Where the server's state lives: the store's rows and the storage's bytes.

``store.py``    the SQLite store, and the reads and writes every part needs
``schema.sql``  its tables, in the v1 schema's shapes
``storage.py``  uploads' and artifacts' bytes, and the grants that reach them

Every id is a UUIDv4: collections order by ``created_at``, the id only a
tiebreaker, so no id needs to sort by time.
'''
