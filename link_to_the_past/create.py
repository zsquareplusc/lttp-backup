#!/usr/bin/env python3
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

from . import config_file_parser, filelist, indexer
from .backup import *

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def len_iter(iterator):
    """Count items in an iterator"""
    n = 0
    for item in iterator:
        n += 1
    return n

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class Create(Backup):
    """Common backup description."""
    def __init__(self):
        Backup.__init__(self)
        self.source_root = filelist.FileList()
        self.backup_root = filelist.FileList()
        self.bytes_required = 0
        self.files_changed = 0
        self.indexer = indexer.Indexer(self.source_root)

    def load_backup_file_list(self):
        self.backup_root.load(os.path.join(self.last_backup_path, 'file_list'))

    def prepare_target(self):
        """Create a new target folder"""
        # create new directory for the backup
        self.base_name = os.path.join(self.target_path, time.strftime('%Y-%m-%d_%02H%02M%02S'))
        self.current_backup_path = self.base_name + '_incomplete'
        logging.debug('Creating backup in {}'.format(self.current_backup_path))
        os.mkdir(self.current_backup_path)
        self.source_root.root = self.current_backup_path
        self.source_root.set_hash(self.hash_name)

    def finalize_target(self):
        """Complete the backup"""
        # write file list
        self.source_root.save(os.path.join(self.current_backup_path, 'file_list'))
        # make backup itself read-only
        os.chmod(self.current_backup_path, stat.S_IRUSR|stat.S_IXUSR|stat.S_IRGRP|stat.S_IXGRP)
        # remove the '_incomplete' suffix
        os.rename(self.current_backup_path, self.base_name)

    def scan_last_backup(self):
        """Find all files in the last backup"""
        # first (or forced) -> full copy
        if self.last_backup_path is None:
            logging.info('No previous backup, create full copy of all items')
        else:
            logging.debug('Checking for changes')
            #~ self.source_root.print_listing()
            #~ self.backup_root.print_listing()
            for root, dirs, files in self.source_root.compare(self.backup_root):
                for entry, other_entry in zip(files.same, files.same_other):
                    entry.changed = False
                    entry.data_hash = other_entry.data_hash
        # count bytes and files to backup
        self.bytes_required = 0
        self.files_changed = 0
        for path, dirs, files in self.source_root.walk():
            for entry in files:
                if entry.changed:
                    self.bytes_required += entry.stat.size
                    self.files_changed += 1

    def check_target(self):
        """Verify that the target is suitable for the backup"""
        # check target path
        if not os.path.exists(self.target_path):
            os.mkdir(self.target_path)
        t = os.statvfs(self.target_path)
        bytes_free = t.f_bsize * t.f_bavail
        if bytes_free < self.bytes_required:
            raise BackupException('not enough free space on target {} available but {} required'.format(
                    filelist.nice_bytes(bytes_free),
                    filelist.nice_bytes(self.bytes_required),
                    ))
        if t.f_favail < len_iter(self.source_root.flattened()):
            raise BackupException('target file system will not allow to create that many files and directories')

    def create(self, force=False, full_backup=False, dry_run=True, confirm=False):
        """Create a backup"""
        # find files to backup
        self.indexer.scan()
        # find latest backup to work incrementally
        if not full_backup:
            self.find_latest_backup()
            if self.last_backup_path is not None:
                self.load_backup_file_list()
                self.source_root.reference = self.last_backup_path
        self.scan_last_backup()
        if not self.files_changed and not force:
            raise BackupException('No changes detected, no need to backup')
        logging.info('Need to copy {} in {} files'.format(filelist.nice_bytes(self.bytes_required), self.files_changed))
        if confirm:
            input('type ENTER to execute')
        # check target
        self.check_target()
        if dry_run:
            for entry in self.source_root.flattened():
                sys.stdout.write('{} {}\n'.format(
                        'COPY' if entry.changed else 'LINK',
                        entry,))
        else:
            t_start = time.time()
            bytes_copied = 0
            # backup files
            self.prepare_target()
            logging.debug('Copying/linking files')
            for p in self.source_root.flattened():
                try:
                    p.create()
                except Exception as e:
                    logging.exception('Error backing up {}: {}'.format(p, e))
                    #~ logging.error('Error backing up %s: %s' % (p, e))
                if p.changed and not isinstance(p, filelist.BackupDirectory):
                    bytes_copied += p.stat.size
                # XXX make this optional
                if self.bytes_required:
                    sys.stderr.write('{:3d}%\r'.format((100.0*bytes_copied/self.bytes_required)))
            # secure directories (make them read-only too)
            logging.debug('Making directories read-only')
            for p in self.source_root.flattened():
                try:
                    p.secure_backup()
                except Exception as e:
                    logging.error('Error securing {}: {}'.format(p, e))
            self.finalize_target()
            time_used = time.time() - t_start
            logging.info('Copied {} in {:.1f} seconds = {}/s'.format(
                    filelist.nice_bytes(self.bytes_required),
                    time_used,
                    filelist.nice_bytes(self.bytes_required/time_used),
                    ))
            logging.info('Created {}'.format(self.base_name))

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def action_create(args):
    b = Create()
    b.evaluate_arguments(args)
    b.create(args.force, args.full, args.dry_run, args.confirm)


def update_argparse(subparsers):
    """Add a subparser for the actions provided by this module"""
    parser = subparsers.add_parser('create')
    group = parser.add_argument_group('Backup Options')
    group.add_argument("-f", "--force",
        help="enforce certain operations (e.g. making a backup even if there are no changes)",
        default=False,
        action='store_true')
    group.add_argument("--full",
        help="always create copy (do not use previous backup to hard link)",
        default=False,
        action='store_true')
    group.add_argument("--dry-run",
        help="do not actually create a backup, only scan the source",
        default=False,
        action='store_true')
    group.add_argument("--confirm",
        help="after scanning, wait for confirmation by user",
        default=False,
        action='store_true')
    parser.set_defaults(func=action_create)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def main():
    import sys
    import doctest
    doctest.testmod()
    sys.exit(0)

if __name__ == '__main__':
    main()
