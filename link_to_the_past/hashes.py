#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""\
Link To The Past - a backup tool

Hash functions and commands.

(C) 2012 cliechti@gmx.net
"""

import hashlib

SUPPORTED_HASHES = {
        'MD5': hashlib.md5,
        'SHA-256': hashlib.sha256,
        'SHA-512': hashlib.sha512,
        }

def get_factory(name):
    return SUPPORTED_HASHES[name.upper()]

