import os
import hashlib
import shutil
import sys

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

def insecure_md5(data):
    '''Wrapper around hashlib md5 function to enable use on FIPS compliant
    platforms.

    This function SHOULD NOT be used for cryptography/security-related purposes.
    '''
    encoded_data = data.encode('utf-8')

    if sys.version_info[0] == 3 and sys.version_info[1] >= 9:
        # usedforsecurity flag added in Python 3.9
        return hashlib.md5(encoded_data, usedforsecurity=False).hexdigest()
    else:
        # Regular md5 call seems to work on FIPS systems when using Python
        # versions older than 3.9.
        return hashlib.md5(encoded_data).hexdigest()
