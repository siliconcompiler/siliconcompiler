import os
import shutil

def copytree(src, dst, ignore=[], dirs_exist_ok=False, link=False):
    '''Simple implementation of shutil.copytree to give us a dirs_exist_ok
    option in Python < 3.8.

    If link is True, create hard links in dst pointing to files in src
    instead of copying them.
    '''
    os.makedirs(dst, exist_ok=dirs_exist_ok)

    for name in os.listdir(src):
        if name in ignore:
            continue

        srcfile = os.path.join(src, name)
        dstfile = os.path.join(dst, name)

        if os.path.isdir(srcfile):
            copytree(srcfile, dstfile, ignore=ignore, dirs_exist_ok=dirs_exist_ok)
        elif link:
            os.link(srcfile, dstfile)
        else:
            shutil.copy2(srcfile, dstfile)
