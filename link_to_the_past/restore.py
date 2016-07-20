#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""\
Link To The Past - a backup tool

Restore and inspection tool.

(C) 2012 cliechti@gmx.net
"""
import os
import stat
import fnmatch
import logging

from . import config_file_parser, filelist, timespec
from .backup import *

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class Restore(Backup):
    def __init__(self):
        Backup.__init__(self)
        self.root = filelist.FileList()

    def load_file_list(self):
        self.root.load(os.path.join(self.current_backup_path, 'file_list'))

    def find_backup_by_time(self, timespec_str=None):
        if timespec_str is None:
            name = self.find_latest_backup()
            self.current_backup_path = self.last_backup_path
        else:
            name = timespec.get_by_timespec(self.find_backups(), timespec_str)
            self.current_backup_path = os.path.join(self.target_path, name)
        if self.current_backup_path is not None:
            logging.info('Active backup: {}'.format(name))
            self.load_file_list()
            self.root.root = self.current_backup_path
        else:
            logging.warning('No backup found')


    def cp(self, source, destination, recursive=False):
        """\
        Copy files or directories from the backup (source) to given
        destination. To copy directories, the recursive flag needs
        to be set, it raises BackupException otherwise.
        """
        item = self.root[source]
        if os.path.isdir(destination):
            destination = os.path.join(destination, item.name)
        if isinstance(item, filelist.BackupDirectory):
            if recursive:
                item.cp(destination, recursive=recursive)
            else:
                raise BackupException('will not work on directories in non-recursive mode: {!r}'.format(source))
        else:
            item.cp(destination)


    @staticmethod
    def populate_arguments(parser):
        #~ Backup.optparse_populate()
        group = parser.add_argument_group('Backup Selection')
        group.add_argument("-t", "--time-spec",
            dest = "timespec",
            help = "load backup matching this time specification",
            default = None,
            action = 'store'
        )

    def evaluate_arguments(self, options):
        Backup.evaluate_arguments(self, options)
        self.find_backup_by_time(options.timespec)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def action_list(args):
    b = Restore()
    b.evaluate_arguments(args)
    backups = b.find_backups()
    backups.sort()
    for name in backups:
        sys.stdout.write('{}\n'.format(name))
    bad_backups = b.find_incomplete_backups()
    if bad_backups:
        logging.warn('Incomplete {} backup(s) detected'.format(len(bad_backups)))


def action_path(args):
    b = Restore()
    b.evaluate_arguments(args)
    sys.stdout.write('{}\n'.format(b.current_backup_path))


def action_ls(args):
    b = Restore()
    b.evaluate_arguments(args)
    if args.PATH:
        path = os.sep + args.PATH
    else:
        path = '*'
    for item in b.root.flattened():
        if fnmatch.fnmatch(item.path, path):
            sys.stdout.write('{}\n'.format(item))


def action_cp(args):
    b = Restore()
    b.evaluate_arguments(args)
    b.cp(args.SRC, args.DST, options.recursive)


def action_cat(args):
    b = Restore()
    b.evaluate_arguments(args)
    item = b.root[args.SRC]
    # XXX set stdout in binary mode
    with open(item.backup_path, 'r') as f:
    #~ with open(item.backup_path, 'rb') as f:
        sys.stdout.write(f.read(2048))


def update_argparse(subparsers):
    """Add a subparser for the actions provided by this module"""
    parser = subparsers.add_parser('list')
    group = parser.add_argument_group('File Selection')
    group.add_argument("-r", "--recursive",
        help="apply operation recursively to all subdirectories",
        default=False,
        action='store_true')
    parser.set_defaults(func=action_list)

    parser = subparsers.add_parser('path')
    Restore.populate_arguments(parser)
    parser.set_defaults(func=action_path)

    parser = subparsers.add_parser('ls')
    parser.add_argument('PATH', nargs='?', default=None)
    Restore.populate_arguments(parser)
    parser.set_defaults(func=action_ls)

    parser = subparsers.add_parser('cp')
    parser.add_argument("-r", "--recursive",
        help="apply operation recursively to all subdirectories",
        default=False,
        action='store_true')
    parser.add_argument('SRC')
    parser.add_argument('DST')
    Restore.populate_arguments(parser)
    parser.set_defaults(func=action_cp)

    parser = subparsers.add_parser('cat')
    parser.add_argument('SRC')
    Restore.populate_arguments(parser)
    parser.set_defaults(func=action_cat)
