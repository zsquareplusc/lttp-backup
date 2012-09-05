#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""\
Link To The Past - a backup tool

Restore and insprection tool.

(C) 2012 cliechti@gmx.net
"""
import os
import stat
import fnmatch
import logging

import config_file_parser
from backup import *

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class FileList(config_file_parser.ContolFileParser):
    """Parser for file lists"""

    def word_p1(self):
        """Parse file info and add it to the internal (file) tree"""
        st_mode = int(self.next_word())
        if stat.S_ISDIR(st_mode):
            entry = BackupDirectory(None, backup=self.backup)
        else:
            entry = BackupFile(backup=self.backup)
        entry.st_mode = st_mode
        entry.st_uid = int(self.next_word())
        entry.st_gid = int(self.next_word())
        entry.st_size = int(self.next_word())
        entry.st_atime = float(self.next_word())
        entry.st_mtime = float(self.next_word())
        st_flags = self.next_word()
        if st_flags != '-':
            entry.st_flags = float(st_flags)
        path = entry.unescape(self.next_word())
        path_elements = path.split(os.sep)
        entry.name = path_elements[-1]
        parent = self.backup.root
        for name in path_elements[1:-1]:
            for p in parent.entries:
                if p.name == name:
                    parent = p
                    break
        entry.parent = parent
        parent.entries.append(entry)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class Restore(Backup):
    def __init__(self):
        Backup.__init__(self)
        self.root = BackupDirectory('/', backup=self)

    def load_file_list(self):
        logging.debug('Loading file list')
        f = FileList(self)
        f.load_file(os.path.join(self.current_backup_path, 'file_list'))

    def find_backup_by_time(self, timespec=None):
        if timespec is None:
            name = self.find_latest_backup()
            self.current_backup_path = self.last_backup_path
        else:
            for name in self.find_backups():
                if timespec in name:
                    self.current_backup_path = os.path.join(self.target_path, name)
                    break
            else:
                raise BackupException('No backup found matching %r' % (timespec,))
        logging.info('Active backup: %s' % (name,))
        self.load_file_list()

    def find_file(self, path):
        for item in self.root.flattened():
            if item.path == path:
                return item
        raise BackupException('not found: %r' % (path,))

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def main():
    import optparse
    import sys

    b = Restore()
    parser = optparse.OptionParser(usage='%prog [options] ACTION [...]')
    b.optparse_populate(parser)

    group = optparse.OptionGroup(parser, 'Backup Selection')
    group.add_option("-t", "--time-spec",
        dest = "timespec",
        help = "load backup matching this time specification",
        default = None,
        action = 'store'
    )
    parser.add_option_group(group)

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
        elif action == 'info':
            b.find_backup_by_time(options.timespec)
            sys.stdout.write('%s\n' % (b.current_backup_path,))
        elif action == 'ls':
            b.find_backup_by_time(options.timespec)
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
            b.find_backup_by_time(options.timespec)
            item = b.find_file(args[0])
            if isinstance(item, BackupDirectory):
                if options.recursive:
                    item.restore(args[1], recursive=options.recursive)
                else:
                    raise BackupException('this is a directory, use -r to restore: %r' % (args[0]))
            else:
                item.restore(args[1])
        elif action == 'cat':
            if len(args) != 1:
                parser.error('expected SRC')
            b.find_backup_by_time(options.timespec)
            item = b.find_file(args[0])
            # XXX set stdout in binary mode
            with open(item.abs_path, 'rb') as f:
                sys.stdout.write(f.read(2048))
        else:
            parser.error('unknown ACTION: %r' % (action,))
    except BackupException as e:
        sys.stderr.write('ERROR: %s\n' % (e))
        sys.exit(1)
    t_end = time.time()
    logging.info('Action took %.1f seconds' % ((t_end - t_start),))


if __name__ == '__main__':
    main()
