#!/usr/bin/env python3
# encoding: utf-8
#
# (C) 2012-2016 Chris Liechti <cliechti@gmx.net>
#
# SPDX-License-Identifier:    BSD-3-Clause
"""\
Link To The Past - a backup tool

Restore and inspection tool.
"""
import os
import shutil
import logging

from . import filelist, timespec
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
        group.add_argument(
            "-t", "--time-spec",
            dest="timespec",
            help="load backup matching this time specification",
            default=None,
            action='store')

    def evaluate_arguments(self, options):
        super().evaluate_arguments(options)
        self.find_backup_by_time(options.timespec)


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def action_list(args):
    """list available backups"""
    b = Backup()
    b.evaluate_arguments(args)
    backups = b.find_backups()
    backups.sort()
    for name in backups:
        sys.stdout.write('{}\n'.format(name))
    bad_backups = b.find_incomplete_backups()
    if bad_backups:
        logging.warn('Incomplete {} backup(s) detected'.format(len(bad_backups)))


def action_path(args):
    """show path to selected backup"""
    b = Restore()
    b.evaluate_arguments(args)
    sys.stdout.write('{}\n'.format(b.current_backup_path))


def action_ls(args):
    """show file list"""
    b = Restore()
    b.evaluate_arguments(args)
    if not args.PATH:
        args.PATH.append('.')

    for path in args.PATH:
        if not os.path.isabs(path):
            path = os.path.abspath(path)
        try:
            item = b.root[path]
        except KeyError as e:
            logging.error('file or directory not found: {}'.format(e))
        else:
            if isinstance(item, filelist.BackupDirectory):
                if args.recursive:
                    for item in item.flattened():
                        sys.stdout.write('{}\n'.format(item))
                else:
                    for x in item:
                        sys.stdout.write('{}\n'.format(x))
            else:
                sys.stdout.write('{}\n'.format(item))


def action_cp(args):
    """copy/extract files/dirs"""
    b = Restore()
    b.evaluate_arguments(args)
    if not os.path.isabs(args.SRC):
        args.SRC = os.path.abspath(args.SRC)
    b.cp(args.SRC, args.DST, args.recursive)


def action_cat(args):
    """show contents of backuped file"""
    b = Restore()
    b.evaluate_arguments(args)
    if not os.path.isabs(args.SRC):
        args.SRC = os.path.abspath(args.SRC)
    try:
        item = b.root[args.SRC]
    except KeyError as e:
        logging.error('file not found: {}'.format(e))
    else:
        # output to stdout in binary mode
        with open(item.backup_path, 'rb') as f:
            shutil.copyfileobj(f, sys.stdout.buffer)


def update_argparse(subparsers):
    """Add a subparser for the actions provided by this module"""
    parser = subparsers.add_parser(
        'list',
        description='List all available backups.',
        help='list available backups')
    parser.set_defaults(func=action_list)

    parser = subparsers.add_parser(
        'path',
        description='Print the absolute path to the directory containing the backup.',
        help='print the path to a backup')
    Restore.populate_arguments(parser)
    parser.set_defaults(func=action_path)

    parser = subparsers.add_parser(
        'ls',
        description='List files/directories contained in backup.',
        help='list the contents of a backup')
    parser.add_argument('PATH', nargs='*')
    parser.add_argument(
        "-r", "--recursive",
        help="apply operation recursively to all subdirectories",
        default=False,
        action='store_true')
    Restore.populate_arguments(parser)
    parser.set_defaults(func=action_ls)

    parser = subparsers.add_parser(
        'cp',
        description='Copy (extract) files or directories from backup.',
        help='copy files from a backup')
    parser.add_argument(
        "-r", "--recursive",
        help="apply operation recursively to all subdirectories",
        default=False,
        action='store_true')
    parser.add_argument('SRC')
    parser.add_argument('DST')
    Restore.populate_arguments(parser)
    parser.set_defaults(func=action_cp)

    parser = subparsers.add_parser(
        'cat',
        description='Copy contents of files of a backup to stdout (binary).',
        help='inspect/show files of a backup')
    parser.add_argument('SRC')
    Restore.populate_arguments(parser)
    parser.set_defaults(func=action_cat)
