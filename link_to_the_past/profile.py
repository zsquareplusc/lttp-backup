#!/usr/bin/env python3
# encoding: utf-8
#
# (C) 2012-2016 Chris Liechti <cliechti@gmx.net>
#
# SPDX-License-Identifier:    BSD-3-Clause
"""\
Link To The Past - a backup tool

Profile management.

A profile is a named configuration located in the directory ~/.link_to_the_past
where the filename is the profile name with '.profile' appended.

The default profile is:
  - A file called ``default.profile`` in the current directory
  - ~/.link_to_the_past/default.profile

(in this order, first that exists is taken)
"""
import os

PROFILE_DIRECTORY = os.path.expanduser('~/.link_to_the_past')
DEFAULT_CURRENT_DIR_NAME = 'default.profile'
DEFAULT_PROFILE_NAME = 'default'


def get_named_profile(name):
    path = os.path.join(PROFILE_DIRECTORY, '{}.profile'.format(name))
    if os.path.exists(path):
        return path
    raise IOError('profile {!r} not found'.format(name))


def get_default_profile():
    if os.path.exists(DEFAULT_CURRENT_DIR_NAME):
        return DEFAULT_CURRENT_DIR_NAME
    return get_named_profile(DEFAULT_PROFILE_NAME)
