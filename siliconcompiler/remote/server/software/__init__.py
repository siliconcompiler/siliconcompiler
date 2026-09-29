'''
What a version means in containers: the software and images this
deployment offers, and how their contents are known.

``images.py``    the registry of software, versions and images, and resolving a
                 job's requirements to them
``probe.py``     what is inside an image, asked rather than declared
``oci.py``       deriving an image in a registry: the base with one layer more
``registry.py``  the operator's command: ``python3 -m
                 siliconcompiler.remote.server.software.registry``
'''
