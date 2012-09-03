#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""\
Link To The Past - a backup tool

(C) 2012 cliechti@gmx.net
"""
import time
import os
import codecs
import fnmatch
import stat
import glob
import shutil
import logging

import config_file_parser
from backup import *

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class Create(Backup):
    """Common backup description."""
    def __init__(self):
        Backup.__init__(self)
        self.enforce_new_backup = False
        self.saved_items = []
        self.bytes_required = 0
        self.files_changed = 0
        self.file_list = None

    def add(self, bpath):
        """Add a file or directory to the items that are backed up"""
        bpath.backup = self
        self.saved_items.append(bpath)

    def prepare_target(self):
        """Create a new target folder"""
        # create new directory for the backup
        self.base_name = os.path.join(self.target_path, time.strftime('%Y-%m-%d_%02H%02M%02S'))
        self.current_backup_path = self.base_name + '_incomplete'
        logging.debug('Creating backup in %s' % (self.current_backup_path,))
        os.mkdir(self.current_backup_path)
        self.file_list = codecs.open(os.path.join(self.current_backup_path, 'file_list'), 'w', 'utf-8')

    def finalize_target(self):
        """Complete the backup"""
        # rename directory
        self.file_list.close()
        self.file_list = None
        os.rename(self.current_backup_path, self.base_name)

    def scan_last_backup(self):
        """Find all files in the last backup"""
        # first (or forced) -> full copy
        if self.last_backup_path is None:
            logging.info('No previous backup, create full copy of all items')
            for item in self.saved_items:
                item.changed = True
        else:
            logging.debug('Checking for changes')
            for item in self.saved_items:
                item.check_changes()
        # count bytes to backup
        self.bytes_required = 0
        self.files_changed = 0
        for item in self.saved_items:
            if isinstance(item, BackupFile) and item.changed:
                self.bytes_required += item.size
                self.files_changed += 1

    def scan_sources(self):
        """Find all files contained in the current backup"""
        for location in self.source_locations:
            location.scan(self)

    def check_target(self):
        """Verify that the target is suitable for the backup"""
        # check target path
        t = os.statvfs(self.target_path)
        bytes_free = t.f_bsize * t.f_bavail
        if bytes_free < self.bytes_required:
            raise BackupException('not enough free space on target %s available but %s required' % (
                    nice_bytes(bytes_free),
                    nice_bytes(self.bytes_required),
                    ))
        if t.f_favail < len(self.saved_items):
            raise BackupException('target file system will not allow to create that many files')

    def create(self, force=False):
        #~ self.read_config()
        # find files to backup
        self.scan_sources()
        # find latest backup to work incrementally
        if not self.enforce_new_backup:
            self.find_latest_backup()
        self.scan_last_backup()
        if not self.files_changed and not force:
            raise BackupException('No changes detected, no need to backup')
        logging.info('Need to copy %d bytes in %d files' % (self.bytes_required, self.files_changed))
        # check target
        self.check_target()
        #~ for p in self.saved_items:
            #~ print p
        # backup files
        self.prepare_target()
        for p in self.saved_items:
            p.create()
            self.file_list.write(p.file_list_command)
        self.finalize_target()
        logging.info('Created %s' % (self.base_name,))

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def main():
    import sys
    import optparse

    parser = optparse.OptionParser(usage='%prog [options]')

    parser.add_option("-c", "--control",
        dest = "control",
        help = "Load control file",
        metavar = 'FILE',
        default = [],
        action = 'append'
    )

    parser.add_option("-f", "--force",
        dest = "force",
        help = "Enforce certain operations (e.g. making a backup even if there is no change)",
        default = False,
        action = 'store_true'
    )

    parser.add_option("--debug",
        dest = "debug",
        help = "Show technical details",
        default = False,
        action = 'store_true'
    )
    parser.add_option("--test-internals",
        dest = "doctest",
        help = "Run internal tests",
        default = False,
        action = 'store_true'
    )
    parser.add_option("-v", "--verbose",
        dest = "verbosity",
        help = "Increase level of messages",
        default = 1,
        action = 'count'
    )
    parser.add_option("-q", "--quiet",
        dest = "verbosity",
        help = "Disable messages (opposite of --verbose)",
        const = 0,
        action = 'store_const'
    )
    (options, args) = parser.parse_args(sys.argv[1:])


    if options.verbosity > 1:
        level = logging.DEBUG
    elif options.verbosity:
        level = logging.INFO
    else:
        level = logging.ERROR
    logging.basicConfig(level=level)

    if options.doctest:
        import doctest
        doctest.testmod()
        sys.exit(0)

    b = Create()
    try:
        b.load_configurations(options.control)
    except IOError as e:
        sys.stderr.write('Failed to load configuration: %s\n' % (e,))
        sys.exit(1)

    try:
        b.create(options.force)
    except BackupException as e:
        sys.stderr.write('ERROR: %s\n' % (e))
        sys.exit(1)


if __name__ == '__main__':
    main()
