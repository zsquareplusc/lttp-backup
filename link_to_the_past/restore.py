#!/usr/bin/env python
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

import config_file_parser
from backup import *

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
        os.chmod(self.path, self.permissions|stat.S_IWUSR)

    def __exit__(self, exc_type, exc_value, traceback):
        os.chmod(self.path, self.permissions)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class FileList(config_file_parser.ContolFileParser):
    """Parser for file lists"""

    def word_hash(self):
        """Set the hash function"""
        if self.backup.hash_name is not None:
            logging.warn('HASH directive found multiple times')
        self.backup.set_hash(self.next_word())

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
        entry.data_hash = self.next_word()
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
        self.root = BackupDirectory(u'/', backup=self)

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

    def cp(self, source, destination, recursive=False):
        """\
        Copy files or directories from the backup (source) to given
        destination. To copy directories, the recursive flag needs
        to be set, it raises BackupException otherwise.
        """
        item = self.find_file(source)
        if os.path.isdir(destination):
            destination = os.path.join(destination, item.name)
        if isinstance(item, BackupDirectory):
            if recursive:
                item.restore(destination, recursive=recursive)
            else:
                raise BackupException('will not work on directories in non-recursive mode: %r' % (source,))
        else:
            item.restore(destination)

    def rm(self, source, recursive=False):
        """\
        Remove a file or a directory (if recursive flag is set).
        This will ultimatively delete the file(s) from the backup!
        """
        item = self.find_file(source)
        if isinstance(item, BackupDirectory):
            if recursive:
                # parent temporarily needs to be writebale to remove files
                with writeable(item.parent.abs_path):
                    # make all sub-entries writable
                    for entry in item.flattened(include_self=True):
                        # directories need to be writeable
                        if isinstance(entry, BackupDirectory):
                            entry.st_mode |= stat.S_IWUSR
                            entry.set_stat(entry.abs_path)
                    # then remove the complete sub-tree
                    shutil.rmtree(item.abs_path)
                item.parent.entries.remove(item)
            else:
                raise BackupException('will not work on directories in non-recursive mode: %r' % (source,))
        else:
            # parent temporarily needs to be writebale to remove files
            with writeable(item.parent.abs_path):
                #~ os.chmod(item.abs_path, stat.S_IWUSR|stat.S_IRUSR)
                os.remove(item.abs_path)
            item.parent.entries.remove(item)
        self.write_file_list()

    def write_file_list(self):
        """Write a new version of the file list"""
        the_copy = os.path.join(self.current_backup_path, 'file_list.new')
        the_original = os.path.join(self.current_backup_path, 'file_list')
        with writeable(self.current_backup_path):
            with codecs.open(the_copy, 'w', 'utf-8') as file_list:
                for p in self.root.flattened():
                    file_list.write(p.file_list_command)
            # make it read-only
            os.chmod(the_copy, stat.S_IRUSR|stat.S_IRGRP)
            # now remove old list and replace with new one
            os.remove(the_original)
            os.rename(the_copy, the_original)

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

    # XXX this is not good if the console is NOT utf-8 capable...
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr)

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
        elif action == 'rm':
            if len(args) != 1:
                parser.error('expected SRC')
            b.find_backup_by_time(options.timespec)
            b.find_file(args[0]) # XXX just test if it is there
            sys.stderr.write('This alters the backup. The file(s) will be lost forever!\n')
            if raw_input('Continue? [y/N]').lower() != 'y':
                sys.stderr.write('Aborted\n')
                sys.exit(1)
            b.rm(args[0], options.recursive)
        elif action == 'cp':
            if len(args) != 2:
                parser.error('expected SRC DST')
            b.find_backup_by_time(options.timespec)
            b.cp(args[0], args[1], options.recursive)
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
