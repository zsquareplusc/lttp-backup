#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""\
Link To The Past - a backup tool

Profile management.

A profile is a named configuration located in the directory
~/.link_to_the_past/profiles where the filename is the profile name.

The default profile is:
  - A file called ``link_to_the_past-configuration`` in the current directory
  - ~/.link_to_the_past/profiles/default

(in this order, first that exists is taken)

(C) 2012 cliechti@gmx.net
"""
import os

PROFILE_DIRECTORY = os.path.expanduser('~/.link_to_the_past/profiles/')
DEFAULT_CURRENT_DIR_NAME = 'link_to_the_past-configuration'
DEFAULT_PROFILE_NAME = 'default'

def get_named_profile(name):
    path = os.path.join(PROFILE_DIRECTORY, name)
    if os.path.exists(path):
        return path
    raise IOError('profile %r not found' % (name,))

def get_default_profile():
    if os.path.exists(DEFAULT_CURRENT_DIR_NAME):
        return DEFAULT_CURRENT_DIR_NAME
    return get_named_profile(DEFAULT_PROFILE_NAME)
