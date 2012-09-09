#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""\
Link To The Past - a backup tool

(C) 2012 cliechti@gmx.net
"""
import time
import sys
import os
import codecs
import glob
import logging
import optparse

import config_file_parser
import profile
#~ import filelist
#~ import indexer

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class BackupException(Exception):
    """A class for backup related errors"""

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class Backup(object):
    """Common backup description."""
    def __init__(self):
        self.target_path = None
        self.current_backup_path = None
        self.last_backup_path = None
        self.base_name = None
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
            logging.debug('Latest backup: %s' % (self.last_backup_path,))
            return backups[-1]
        else:
            logging.info('No previous backup found')

    def load_configuration(self, filename):
        logging.debug('Loading configuration %s' % (filename,))
        c = BackupControl(self)
        c.load_file(filename)
        if self.target_path is None:
            raise BackupException('Configuration misses TARGET directive')

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def optparse_populate(self, parser):
        """Adds common options to the parser"""

        group = optparse.OptionGroup(parser, 'Messages')
        group.add_option("--debug",
            dest = "debug",
            help = "show technical details",
            default = False,
            action = 'store_true'
        )
        group.add_option("-v", "--verbose",
            dest = "verbosity",
            help = "increase level of messages",
            default = 1,
            action = 'count'
        )
        group.add_option("-q", "--quiet",
            dest = "verbosity",
            help = "disable messages (opposite of --verbose)",
            const = 0,
            action = 'store_const'
        )
        parser.add_option_group(group)

        group = optparse.OptionGroup(parser, 'Backup Configuration')
        group.add_option("-c", "--control",
            dest = "control",
            help = "load control file",
            metavar = 'FILE',
            default = None,
        )
        group.add_option("-p", "--profile",
            dest = "profile",
            help = "load named profile",
            metavar = 'NAME',
            default = None,
        )
        parser.add_option_group(group)

    def optparse_evaluate(self, options):
        """Apply the effects of the common options"""
        if options.verbosity > 1:
            level = logging.DEBUG
        elif options.verbosity:
            level = logging.INFO
        else:
            level = logging.ERROR
        logging.basicConfig(level=level)

        if options.control is None:
            if options.profile is not None:
                options.control = profile.get_named_profile(options.profile)
            else:
                options.control = profile.get_default_profile()
        try:
            self.load_configuration(options.control)
        except IOError as e:
            sys.stderr.write('ERROR: Failed to load configuration: %s\n' % (e,))
            sys.exit(1)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class BackupControl(config_file_parser.ContolFileParser):
    """Parser for backup control files"""

    def __init__(self, backup):
        config_file_parser.ContolFileParser.__init__(self)
        self.backup = backup

    def word_target(self):
        self.backup.set_target_path(self.path(self.next_word()))

    def word_include(self):
        path = self.next_word()
        if self.backup.indexer is not None:
            self.backup.indexer.includes.append(indxer.Location(self.path(path)))

    def word_exclude(self):
        path = self.next_word()
        if self.backup.indexer is not None:
            self.backup.indexer.excludes.append(indexer.ShellPattern(path))

    def word_hash(self):
        """Set the hash function"""
        if self.backup.root.hash_name is not None:
            logging.warn('HASH directive found multiple times')
        self.backup.root.set_hash(self.next_word())

    def word_load_config(self):
        """include an other configuration file"""
        c = self.__class__(self.backup)
        path = self.next_word()
        c.load_file(path)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

if __name__ == '__main__':

    import doctest
    doctest.testmod()

