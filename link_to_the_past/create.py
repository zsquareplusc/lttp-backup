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
        self.root = BackupDirectory(u'/', backup=self)
        self.bytes_required = 0
        self.files_changed = 0
        self.file_list = None

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
        # finish file list
        self.file_list.close()
        self.file_list = None
        # make file list also read only
        os.chmod(os.path.join(self.current_backup_path, 'file_list'), stat.S_IRUSR|stat.S_IRGRP)
        # remove the '_incomplete' suffix
        os.rename(self.current_backup_path, self.base_name)

    def scan_last_backup(self):
        """Find all files in the last backup"""
        # first (or forced) -> full copy
        if self.last_backup_path is None:
            logging.info('No previous backup, create full copy of all items')
            for item in self.root.flattened():
                item.changed = True
        else:
            logging.debug('Checking for changes')
            for item in self.root.flattened():
                item.check_changes()
        # count bytes to backup
        self.bytes_required = 0
        self.files_changed = 0
        for item in self.root.flattened():
            if item.changed and not isinstance(item, BackupDirectory):
                self.bytes_required += item.size
                self.files_changed += 1

    def scan_sources(self):
        """Find all files contained in the current backup"""
        for location in self.source_locations:
            location.scan(self.root)

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
        if t.f_favail < len(list(self.root.flattened())): # XXX list is bad
            raise BackupException('target file system will not allow to create that many files')

    def create(self, force=False, full_backup=False, dry_run=True):
        """Create a backup"""
        # find files to backup
        self.scan_sources()
        # find latest backup to work incrementally
        if not full_backup:
            self.find_latest_backup()
        self.scan_last_backup()
        if not self.files_changed and not force:
            raise BackupException('No changes detected, no need to backup')
        logging.info('Need to copy %s in %d files' % (nice_bytes(self.bytes_required), self.files_changed))
        # check target
        self.check_target()
        if dry_run:
            for entry in self.root.flattened(include_self=True):
                sys.stdout.write('%s\n' % (entry,))
        else:
            # backup files
            self.prepare_target()
            logging.debug('Copying/linking files')
            for p in self.root.flattened():
                p.create()
                self.file_list.write(p.file_list_command)
            # secure directories (make then read-only too)
            logging.debug('Making directories read-only')
            for p in self.root.flattened():
                p.secure()
            self.finalize_target()
            logging.info('Created %s' % (self.base_name,))

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def main():
    import sys
    import optparse

    b = Create()
    parser = optparse.OptionParser(usage='%prog [options]')
    b.optparse_populate(parser)

    group = optparse.OptionGroup(parser, 'Backup Options')
    group.add_option("-f", "--force",
        dest = "force",
        help = "enforce certain operations (e.g. making a backup even if there are no changes)",
        default = False,
        action = 'store_true'
    )
    group.add_option("--full",
        dest = "full_backup",
        help = "always create copy (do not use previous backup to hard link)",
        default = False,
        action = 'store_true'
    )
    group.add_option("--dry-run",
        dest = "dry_run",
        help = "do not actually create a backup, only scan the source",
        default = False,
        action = 'store_true'
    )
    parser.add_option_group(group)

    (options, args) = parser.parse_args(sys.argv[1:])

    # XXX this is not good if the console is NOT utf-8 capable...
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr)

    b.optparse_evaluate(options)

    parser.add_option("--test-internals",
        dest = "doctest",
        help = "Run internal tests",
        default = False,
        action = 'store_true'
    )
    (options, args) = parser.parse_args(sys.argv[1:])


    if options.doctest:
        import doctest
        doctest.testmod()
        sys.exit(0)


    t_start = time.time()
    try:
        b.create(options.force, options.full_backup, options.dry_run)
    except BackupException as e:
        sys.stderr.write('ERROR: %s\n' % (e))
        sys.exit(1)
    t_end = time.time()
    logging.info('Backup took %.1f seconds' % ((t_end - t_start),))


if __name__ == '__main__':
    main()
