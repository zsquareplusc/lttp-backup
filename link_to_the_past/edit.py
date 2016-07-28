#!/usr/bin/env python3
# encoding: utf-8
#
# (C) 2012-2016 Chris Liechti <cliechti@gmx.net>
#
# SPDX-License-Identifier:    BSD-3-Clause
"""\
Link To The Past - a backup tool

Modify backups.

Sometimes it is even useful to edit backups. E.g. to remove files or
directories that have been archived by accident.

Actions to delete backups are also here. A specific backup can be
deleted and there is an automatic delete function that keeps less
backups the further back in time they were made.
"""

import shutil

from .restore import *
from .error import BackupException


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class writeable(object):
    """\
    Context manager that chmod's the given path to make it writeable.
    The original permissions are restored on exit.
    """
    def __init__(self, path):
        self.path = path
        self.permissions = os.lstat(path).st_mode

    def __enter__(self):
        os.chmod(self.path, self.permissions | stat.S_IWUSR)

    def __exit__(self, exc_type, exc_value, traceback):
        os.chmod(self.path, self.permissions)


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class EditBackup(Restore):

    def write_file_list(self):
        """Write a new version of the file list"""
        with writeable(self.current_backup_path):
            self.root.save(os.path.join(self.current_backup_path, 'file_list'))

    def rm(self, source, recursive=False, force=False):
        """\
        Remove a file or a directory (if recursive flag is set).
        This will ultimately delete the file(s) from the backup!
        """
        item = self.root[source]
        if isinstance(item, filelist.BackupDirectory):
            if recursive:
                # parent temporarily needs to be writeable to remove files
                with writeable(item.parent.backup_path):
                    # make all sub-entries writable
                    for entry in item.flattened(include_self=True):
                        # directories need to be writeable
                        if isinstance(entry, filelist.BackupDirectory):
                            entry.stat.mode |= stat.S_IWUSR
                            entry.stat.write(entry.backup_path, chmod_only=True)
                    # then remove the complete sub-tree
                    shutil.rmtree(item.backup_path)
                item.parent.entries.remove(item)
            else:
                raise BackupException('will not work on directories in non-recursive mode: {!r}'.format(filelist.escaped(source)))
        else:
            # parent temporarily needs to be writeable to remove files
            with writeable(item.parent.backup_path):
                #~ os.chmod(item.abs_path, stat.S_IWUSR|stat.S_IRUSR)
                try:
                    os.remove(item.backup_path)
                except OSError as e:
                    if force:
                        logging.warning('could not remove file: {}'.format(e))
                    else:
                        raise BackupException('could not remove file: {}'.format(e))
            item.parent.entries.remove(item)
        self.write_file_list()

    def purge(self):
        """Remove the entire backup"""
        # make the backup writeable
        os.chmod(self.current_backup_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        # make all sub-directoris writable, needed for rmdir
        for path, dirs, files in self.root.walk():
            # directories need to be writeable
            for directory in dirs:
                directory.stat.mode |= stat.S_IWUSR
                directory.stat.write(directory.backup_path, chmod_only=True)
        # then remove the complete tree
        shutil.rmtree(self.current_backup_path)


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def ask_the_question():
    sys.stderr.write('This alters the backup. The file(s) will be lost forever!\n')
    if input('Continue? [y/N] ').lower() != 'y':
        sys.stderr.write('Aborted\n')
        sys.exit(1)


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def action_rm(args):
    """remove files/directories from backup"""
    b = EditBackup()
    b.evaluate_arguments(args)
    entry = b.root[args.SRC]  # XXX just test if it is there. catch ex and print error
    sys.stderr.write('Going to remove {}\n'.format(filelist.escaped(entry.path)))
    ask_the_question()
    b.rm(args.SRC, args.recursive, args.force)


def action_purge(args):
    """remove entire backups"""
    b = EditBackup()
    b.evaluate_arguments(args)
    sys.stderr.write('Going to remove the entire backup: {}\n'.format(os.path.basename(b.current_backup_path)))
    ask_the_question()
    b.purge()


def update_argparse(subparsers):
    """Add a subparser for the actions provided by this module"""
    parser = subparsers.add_parser(
        'rm',
        description='Remove files or directories from backup.',
        help='remove files/dirs from backups')
    parser.add_argument('SRC')
    group = parser.add_argument_group('File Selection')
    group.add_argument(
        "-f", "--force",
        help="enforce certain operations",
        default=False,
        action='store_true')
    group.add_argument(
        "-r", "--recursive",
        help="apply operation recursively to all subdirectories",
        default=False,
        action='store_true')
    Restore.populate_arguments(parser)
    parser.set_defaults(func=action_rm)

    parser = subparsers.add_parser(
        'purge',
        description='Remove entire backups.',
        help='remove entire backups')
    Restore.populate_arguments(parser)
    parser.set_defaults(func=action_purge)
