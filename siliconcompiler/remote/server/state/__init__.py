'''
Where the server's state lives: the store's rows and the storage's bytes.

``store.py``    the SQLite store, and the reads and writes every part needs
``schema.sql``  its 18 tables, whose shapes are the contract crucible implements
``storage.py``  where uploads and artifacts' bytes live, and the grants that let
                a client at them
``ids.py``      UUIDv7 identifiers, time-sortable, so a keyset cursor is the id
'''
