#!/usr/bin/env python3
# encoding: utf-8
#
# (C) 2012-2016 Chris Liechti <cliechti@gmx.net>
#
# SPDX-License-Identifier:    BSD-3-Clause
"""\
Link To The Past - a backup tool

Compare backups and sources.
"""

from .restore import *
from .create import *
from . import filelist
from .string_escape import escaped


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def print_changes(iterator, long_format, show_all=False):
    for root, dirs, files in iterator:
        # sort by name again
        entries = []
        if show_all:
            entries.extend((entry, ' ') for entry in files.same)
        entries.extend((entry, 'M') for entry in files.changed)
        entries.extend((entry, 'A') for entry in files.added)
        entries.extend((entry, 'R') for entry in files.removed)
        if show_all:
            entries.extend((entry, ' ') for entry in dirs.same)
        entries.extend((entry, 'A') for entry in dirs.added)
        entries.extend((entry, 'R') for entry in dirs.removed)
        entries.sort()
        for entry, status in entries:
            if long_format:
                sys.stdout.write('{} {}\n'.format(status, entry))
            else:
                sys.stdout.write('{} {}\n'.format(status, entry.path))
        #~ for e1, e2 in zip(files.changed, files.changed_other):
            #~ print "<--", e1
            #~ print "-->", e2


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def action_verify(args):
    """compare hashes in source with saved file list"""
    b = Restore()
    b.evaluate_arguments(args)
    # XXX allow '.' and find out which dir it is
    #~ if args:
        #~ path = os.sep + args[0]
    #~ else:
        #~ path = '*'
    scan = Create()
    scan.evaluate_arguments(args)
    scan.source_root.set_hash(scan.hash_name)   # shouldn't this be done automatically?
    scan.indexer.scan()
    # XXX this calculates the hash of added files for which we can not compare the hash. wasted time :/
    for path, dirs, files in scan.source_root.walk():
        for entry in files:
            entry.update_hash_from_source()
    print_changes(scan.source_root.compare(b.root), args.long)


def action_integrity(args):
    """compare hashes in backup with saved file list"""
    b = Restore()
    b.evaluate_arguments(args)
    #~ logging.debug('scanning {}...'.format(b.root))
    for path, dirs, files in b.root.walk():
        for entry in dirs:
            logging.debug('checking {}'.format(escaped(entry.path)))
            if not os.path.isdir(entry.backup_path):
                sys.stdout.write('MISSING {}\n'.format(escaped(entry.path)))
        for entry in files:
            logging.debug('checking {}'.format(escaped(entry.path)))
            status = 'OK'
            if os.path.exists(entry.backup_path):
                if not entry.verify_hash(entry.backup_path):
                    status = 'CORRUPTED'
            else:
                status = 'MISSING'
            sys.stdout.write('{} {}\n'.format(status, escaped(entry.path)))


def action_changes(args):
    """compare changes between two backups"""
    if args.TIMESPEC2 == 'now':
        # "now" as word to scan sources instead of loading a backup
        # swap order between b and other as now is "newer"..
        other_backup = Restore()
        other_backup.evaluate_arguments(args)
        b = Create()
        b.evaluate_arguments(args)
        b.target_path = other_backup.target_path
        b.source_root.set_hash(other_backup.hash_name)   # shoun't this be done automatically?
        b.indexer.scan()
        b.root = b.source_root
    else:
        b = Restore()
        b.evaluate_arguments(args)
        other_backup = Restore()
        other_backup.target_path = b.target_path
        other_backup.find_backup_by_time(args.TIMESPEC2)
    if b.current_backup_path == other_backup.current_backup_path:
        raise BackupException('Both TIMESPECs point to the same backup')
    print_changes(b.root.compare(other_backup.root), args.long, args.all)


def update_argparse(subparsers):
    """Add a sub-parser for the actions provided by this module"""
    parser = subparsers.add_parser(
        'verify',
        description='Compare current files to the checksums stored in the '
                    'backup. This is a slow operation as it needs to read '
                    'all files.',
        help='compare current files against file list in backup')
    group = parser.add_argument_group('Display Options')
    group.add_argument(
        "-l", "--long",
        help="show detailed file info",
        default=False,
        action='store_true')
    Restore.populate_arguments(parser)
    parser.set_defaults(func=action_verify)

    parser = subparsers.add_parser(
        'integrity',
        description='Check the files in the backup against modifications by '
                    'comparing them with the checksum in the file list. This '
                    'is a slow operation as it needs to read all files.',
        help='verify backup against its file list')
    Restore.populate_arguments(parser)
    parser.set_defaults(func=action_integrity)

    parser = subparsers.add_parser(
        'changes',
        description='Compare current files or a second backup with filelist '
                    'from backup (timestamps only). If TIMESPEC2 is "now", '
                    'the current files are checked.',
        help='show changed files compared to backup or now')
    parser.add_argument('TIMESPEC2', help='specify other backup or "now" for current files')
    group = parser.add_argument_group('Display Options')
    group.add_argument(
        "-l", "--long",
        help="show detailed file info",
        default=False,
        action='store_true')
    group.add_argument(
        "-a", "--all",
        help="only show all, not only modified items",
        default=False,
        action='store_true')
    Restore.populate_arguments(parser)
    parser.set_defaults(func=action_changes)
