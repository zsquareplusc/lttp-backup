#!/usr/bin/env python3
# encoding: utf-8
#
# (C) 2012-2016 Chris Liechti <cliechti@gmx.net>
#
# SPDX-License-Identifier:    BSD-3-Clause
"""\
Link To The Past - a backup tool
"""
import sys
import os
import glob
import logging

from . import config_file_parser, profile, indexer
#~ import filelist
from .error import BackupException

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Backup(object):
    """Common backup description."""
    def __init__(self):
        self.target_path = None
        self.current_backup_path = None
        self.last_backup_path = None
        self.base_name = None
        self.hash_name = None
        self.indexer = None

    def set_target_path(self, path):
        """Set the path to the backups (a directory)"""
        self.target_path = os.path.normpath(path)

    def find_backups(self):
        """Return a list of names, of complete backups"""
        backups = glob.glob(os.path.join(self.target_path, '????-??-??_??????'))
        return [name[len(self.target_path)+len(os.sep):] for name in backups]

    def find_incomplete_backups(self):
        """Return a list of names, of incomplete backups"""
        backups = glob.glob(os.path.join(self.target_path, '????-??-??_??????_incomplete'))
        return [name[len(self.target_path)+len(os.sep):] for name in backups]

    def find_latest_backup(self):
        """Locate the last backup. It is used as reference"""
        backups = self.find_backups()
        if backups:
            backups.sort()
            self.last_backup_path = os.path.join(self.target_path, backups[-1])
            logging.debug('Latest backup: {}'.format(self.last_backup_path))
            return backups[-1]
        else:
            logging.info('No previous backup found')

    def load_configuration(self, filename):
        logging.debug('Loading configuration {}'.format(filename))
        c = BackupControl(self)
        c.load_file(filename)
        if self.target_path is None:
            raise BackupException('Configuration misses TARGET directive')

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def evaluate_arguments(self, args):
        """Apply the effects of the common options"""
        if args.profile is not None:
            args.control = profile.get_named_profile(args.profile)
        if args.control is None:
            args.control = profile.get_default_profile()
        try:
            self.load_configuration(args.control)
        except IOError as e:
            sys.stderr.write('ERROR: Failed to load configuration: {}\n'.format(e))
            sys.exit(1)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class BackupControl(config_file_parser.ControlFileParser):
    """\
    Parser for backup control files, takes a backup object and configures it
    based on the config file.
    """

    def __init__(self, backup):
        super().__init__()
        self.backup = backup

    def word_target(self):
        """set the target location"""
        self.backup.set_target_path(self.path(self.next_word()))

    def word_include(self):
        """include a path to the backup"""
        path = self.next_word()
        if self.backup.indexer is not None:
            self.backup.indexer.includes.append(indexer.Location(self.path(path)))

    def word_exclude(self):
        """exclude a path from the backup"""
        path = self.next_word()
        if self.backup.indexer is not None:
            self.backup.indexer.excludes.append(indexer.ShellPattern(path))

    def word_hash(self):
        """Set the hash function"""
        if self.backup.hash_name is not None:
            logging.warn('HASH directive found multiple times')
        self.backup.hash_name = self.next_word()

    def word_load_config(self):
        """include an other configuration file"""
        c = self.__class__(self.backup)
        path = str(self.next_word())
        if not os.path.isabs(path):
            path = os.path.join(self.root, path)
        c.load_file(path)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

if __name__ == '__main__':
    import doctest
    doctest.testmod()
