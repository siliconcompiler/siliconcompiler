'''
Where the server's state lives: the store's rows and the storage's bytes.

``store.py``    the SQLite store, and the reads and writes every part needs
``schema.sql``  its 18 tables, whose shapes are the contract crucible implements
``storage.py``  where uploads and artifacts' bytes live, and the grants that let
                a client at them

Every id is a UUIDv4, opaque to clients. The contract leaves v4 or v7 to the
deployment, and orders every collection by ``created_at`` with the id only as
a tiebreaker, so no id needs to sort by when it was minted.
'''
