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
            logging.info('Active backup: %s' % (name,))
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
                raise BackupException('will not work on directories in non-recursive mode: %r' % (source,))
        else:
            item.cp(destination)


    def optparse_populate(self, parser):
        Backup.optparse_populate(self, parser)
        group = optparse.OptionGroup(parser, 'Backup Selection')
        group.add_option("-t", "--time-spec",
            dest = "timespec",
            help = "load backup matching this time specification",
            default = None,
            action = 'store'
        )
        parser.add_option_group(group)

    def optparse_evaluate(self, options):
        Backup.optparse_evaluate(self, options)
        self.find_backup_by_time(options.timespec)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
IMPLEMENTED_ACTIONS = ['list', 'path', 'ls', 'cp', 'cat']

def main():
    import optparse
    import sys

    b = Restore()
    parser = optparse.OptionParser(usage='%prog [options] ACTION [...]')
    b.optparse_populate(parser)

    group = optparse.OptionGroup(parser, 'File Selection')
    group.add_option("-r", "--recursive",
        dest = "recursive",
        help = "apply operation recursively to all subdirectories",
        default = False,
        action = 'store_true'
    )
    parser.add_option_group(group)

    (options, args) = parser.parse_args(sys.argv[1:])

    b.optparse_evaluate(options)


    if not args:
        parser.error('Expected ACTION')
    action = args.pop(0)

    t_start = time.time()
    try:
        if action == 'list':
            backups = b.find_backups()
            backups.sort()
            for name in backups:
                sys.stdout.write('%s\n' % (name,))
            bad_backups = b.find_incomplete_backups()
            if bad_backups:
                logging.warn('Incomplete %d backup(s) detected' % (len(bad_backups),))
        elif action == 'path':
            sys.stdout.write('%s\n' % (b.current_backup_path,))
        elif action == 'ls':
            if args:
                path = os.sep + args[0]
            else:
                path = '*'
            for item in b.root.flattened():
                if fnmatch.fnmatch(item.path, path):
                    sys.stdout.write('%s\n' % (item,))
        elif action == 'cp':
            if len(args) != 2:
                parser.error('expected SRC DST')
            b.cp(args[0], args[1], options.recursive)
        elif action == 'cat':
            if len(args) != 1:
                parser.error('expected SRC')
            item = b.root[args[0]]
            # XXX set stdout in binary mode
            with open(item.backup_path, 'rb') as f:
                sys.stdout.write(f.read(2048))
        else:
            parser.error('unknown ACTION: %r' % (action,))
    except KeyboardInterrupt:
        sys.stderr.write('\nAborted on user request.\n')
        sys.exit(1)
    except BackupException as e:
        sys.stderr.write('ERROR: %s\n' % (e))
        sys.exit(1)
    t_end = time.time()
    logging.info('Action took %.1f seconds' % ((t_end - t_start),))


if __name__ == '__main__':
    main()
