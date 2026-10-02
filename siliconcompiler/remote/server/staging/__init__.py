'''
What happens between submit and `queued`: the upload opened, the
manifest read, and the sources the run needs fetched.

``archive.py``        opening somebody else's archive, held to the limits
``manifestread.py``   the one place a manifest is read, in a process of its own
``sandbox.py``        starting that read, and holding it to its limits
``schemaclasses.py``  the classes a manifest may name, and nothing imported for it
``sources.py``        the server's own copies of remote sources, and fetching them
``fetch.py``          one source fetched in a process of its own, held in from outside
``allowlist.py``      where the server will fetch from, and where an install may reach
'''
