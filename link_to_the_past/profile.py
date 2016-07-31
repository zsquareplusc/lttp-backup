#!/usr/bin/env python3
# encoding: utf-8
#
# (C) 2012-2016 Chris Liechti <cliechti@gmx.net>
#
# SPDX-License-Identifier:    BSD-3-Clause
"""\
Link To The Past - a backup tool

Profile management.

A profile is a named configuration located in the directory
$XDG_CONFIG_HOME/link-to-the-past-backup (if XDG_CONFIG_HOME is not set, a
value of $HOME/.config is assumed) where the filename is the profile name with
'.profile' appended.

https://standards.freedesktop.org/basedir-spec/basedir-spec-latest.html
"""
import os

DEFAULT_PROFILE_NAME = 'default'

config_directory = os.environ.get(
    'XDG_CONFIG_HOME',
    os.path.join(os.environ.get('HOME', '~'), '.config'))

profile_directory = os.path.expandvars(
    os.path.join(config_directory, 'link-to-the-past-backup'))


def get_named_profile(name):
    path = os.path.join(profile_directory, '{}.profile'.format(name))
    if os.path.exists(path):
        return path
    raise IOError('profile {!r} not found in {}'.format(name, profile_directory))


def get_default_profile():
    return get_named_profile(DEFAULT_PROFILE_NAME)
