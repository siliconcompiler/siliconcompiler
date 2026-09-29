'''
A job's Python packages, installed while the job stages (surface
*A node's own Python packages, built while staging*).

``envinstall.py``  on the host, into the user's cache, where nodes run here
``envbuild.py``    into a derived image, in the isolated builder, where nodes run
                   in containers
``pipbuild.py``    the install both run -- standard library only, run as a file
                   under the target's own Python
'''
