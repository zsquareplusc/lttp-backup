#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""\
Link To The Past - a backup tool

Hash functions and commands.

(C) 2012 cliechti@gmx.net
"""

import hashlib
import zlib

class CRC32Hash(object):
    """\
    CRC32 API compatible to the hashlib functions (subset used by this program).

    >>> h = CRC32Hash()
    >>> h.update('Hello World')
    >>> h.hexdigest()
    '4a17b156'
    """

    def __init__(self):
        self.value = 0

    def update(self, data):
        self.value = zlib.crc32(data, self.value) & 0xffffffff

    def hexdigest(self):
        return '%08x' % (self.value,)


class NoHash(object):
    """\
    API compatible to the hashlib functions (subset used by this program).

    >>> h = CRC32Hash()
    >>> h.update('Hello World')
    >>> h.hexdigest()
    '-'
    """

    def __init__(self):
        pass

    def update(self, data):
        pass

    def hexdigest(self):
        return '-'

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

SUPPORTED_HASHES = {
        'NONE':     NoHash,
        'CRC32':    CRC32Hash,
        'MD5':      hashlib.md5,
        'SHA-256':  hashlib.sha256,
        'SHA-512':  hashlib.sha512,
        }

def get_factory(name):
    """\
    Get an object for calculating a hash.
    >>> f = get_factory('SHA-256')
    >>> h = f()
    >>> h.update('Hello World')
    >>> h.hexdigest()
    'a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e'
    """
    if name is None: name = 'NONE'
    return SUPPORTED_HASHES[name.upper()]

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

if __name__ == '__main__':
    import doctest
    doctest.testmod()

