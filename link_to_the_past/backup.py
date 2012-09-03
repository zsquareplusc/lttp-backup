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

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
EXPONENTS = ('', 'k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')

def nice_bytes(value):
    """\
    Return a string for a number representing bytes in a human readable form
    (1kB=1000B as usual for storage devices now days).

    >>> nice_bytes(1024)
    '1.024kB'
    >>> nice_bytes(2e9)
    '2.000GB'
    """
    if value < 0: raise ValueError('Byte count can not be negative: %s' % (value,))
    value = float(value)
    exp = 0
    while value >= 1000 and exp < len(EXPONENTS):
        value /= 1000
        exp += 1
    return '%.3f%sB' % (value, EXPONENTS[exp])

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class BackupException(Exception):
    """A class for backup related errors"""

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class BackupPath(object):
    """Representing an object that is contained in the backup"""
    __slots__ = ['path', 'backup', 'changed', 'st_size', 'st_mode', 'st_uid', 'st_gid', 'st_mtime']

    def __init__(self, path=None):
        self.path = path
        self.backup = None
        if path is not None:
            stat_now = os.lstat(path)
            self.st_size = stat_now.st_size
            self.st_uid = stat_now.st_uid
            self.st_gid = stat_now.st_gid
            self.st_mode = stat_now.st_mode
            self.st_mtime = stat_now.st_mtime
        self.changed = False
        # XXX track changes of contents and meta data separately?

    @property
    def size(self):
        return self.st_size

    def __str__(self):
        return self.path

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.path)

    def join(self, root, path):
        return os.path.normpath('%s%s%s' % (root, os.sep, path))

    def escaped(self, path):
        """Escape control non printable characters and the space"""
        return path.encode('unicode-escape').replace(' ', '\\ ')

    def unescape(self, path):
        """Escape control non printable characters and the space"""
        return path.decode('unicode-escape').replace('\\ ', ' ')


class BackupFile(BackupPath):
    """Information about a file as well as operations"""
    __slots__ = []

    def check_changes(self):
        """Compare the original file with the backup"""
        prev = os.lstat(os.path.join(self.backup.last_backup_path, self.path))
        #~ if (    self.stat_now.st_mode != prev.st_mode or
                #~ self.stat_now.st_uid != prev.st_uid or
                #~ self.stat_now.st_gid != prev.st_gid or
                #~ self.stat_now.st_size != prev.st_size or
                #~ self.stat_now.st_mode != prev.st_mode or
                #~ abs(self.stat_now.st_mtime - prev.st_mtime) > 0.00001): # as it is a float...
        # ignore changes in meta data. just look at the contents
        if (self.st_size != prev.st_size or
                abs(self.st_mtime - prev.st_mtime) > 0.00001): # 10us; as it is a float...
            self.changed = True

    def copy(self):
        """Create a copy of the file"""
        logging.debug('copying %s' % (self.escaped(self.path),))
        dst = self.join(self.backup.current_backup_path, self.path)
        if os.path.islink(self.path):
            linkto = os.readlink(self.path)
            os.symlink(linkto, dst)
        else:
            shutil.copy2(self.path, dst)
        # XXX make read-only

    def link(self):
        """Create a hard link for the file"""
        logging.debug('hard linking %s' % (self.escaped(self.path),))
        src = self.join(self.backup.last_backup_path, self.path)
        dst = self.join(self.backup.current_backup_path, self.path)
        os.link(src, dst)
        shutil.copystat(src, dst)

    def create(self):
        """Backup the file, either by hard linking or copying"""
        if self.changed:
            self.copy()
        else:
            self.link()

    @property
    def file_list_command(self):
        return 'f %s %s %s %s %.6f %s\n' % (
                self.st_mode,
                self.st_uid,
                self.st_gid,
                self.st_size,
                self.st_mtime,
                self.escaped(self.path))

    def restore(self, dst):
        """Create a copy of the file"""
        logging.debug('copying %s' % (self.escaped(self.path),))
        src = self.join(self.backup.current_backup_path, self.path)
        if os.path.islink(src):
            linkto = os.readlink(src)
            os.symlink(linkto, dst)
        else:
            shutil.copy2(src, dst)


class BackupDirectory(BackupPath):
    """Information about a directory as well as operations"""

    def check_changes(self):
        """Directories are always created"""
        self.changed = True

    def create(self):
        """Directories are always created"""
        logging.debug('new directory %s' % (self.path,))
        dst = self.join(self.backup.current_backup_path, self.path)
        os.makedirs(dst)
        #~ try:
        shutil.copystat(self.path, dst)
        #~ except WindowsError:
            #~ # can't copy file access times on Windows
            #~ pass
        # XXX make read-only

    @property
    def file_list_command(self):
        return 'dir %s %s %s %.6f %s\n' % (
                self.st_mode,
                self.st_uid,
                self.st_gid,
                self.st_mtime,
                self.escaped(self.path))

    def restore(self, dst):
        """Directories are always created"""
        logging.debug('new directory %s' % (self.path,))
        src = self.join(self.backup.current_backup_path, self.path)
        os.makedirs(dst)
        #~ try:
        shutil.copystat(src, dst)
        #~ except WindowsError:
            #~ # can't copy file access times on Windows
            #~ pass

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class ShellPattern(object):
    """A shell like pattern to test filenames"""
    def __init__(self, pattern):
        self.pattern = pattern

    def __repr__(self):
        return 'ShellPattern(%r)' % (self.pattern,)

    def matches(self, filename):
        return fnmatch.fnmatch(filename, self.pattern)


class Location(object):
    """A location on the file system, user as source for backups"""
    def __init__(self, path):
        self.path = os.path.normpath(path)
        self.excludes = []

    def __repr__(self):
        return 'Location(%r)' % (self.path,)

    #~ def relative_path(self, path):
        #~ if os.path.isabs(path):
            #~ norm_path = os.path.normpath(path)
            #~ if norm_path.startswith(self.path):
                #~ path = path[len(os.pathsep)+len(self.path):]
        #~ return path

    def filtered(self, names):
        for name in names:
            included = True
            for exclude in self.excludes:
                if exclude.matches(name):
                    included = False
                    break
            if included:
                yield name

    def scan(self, backup):
        """Find all files in the source directory"""
        # scan and handle excluded files on the fly
        backup.add(BackupDirectory(self.path))
        for root, dirs, files in os.walk(self.path):
            for name in self.filtered(files):
                backup.add(BackupFile(os.path.join(root, name)))
            # do not visit directories matching excludes
            included_dirs = self.filtered(dirs)
            for name in list(dirs): # iterate over copy
                if name not in included_dirs:
                    dirs.remove(name)
                else:
                    backup.add(BackupDirectory(os.path.join(root, name)))


class Backup(object):
    """Common backup description."""
    def __init__(self):
        self.source_locations = []
        self.target_path = None
        self.current_backup_path = None
        self.last_backup_path = None
        self.base_name = None

    def set_target_path(self, path):
        self.target_path = os.path.normpath(path)

    def find_backups(self):
        backups = glob.glob(os.path.join(self.target_path, '????-??-??_??????'))
        return [name[len(self.target_path)+len(os.sep):] for name in backups]

    def find_incomplete_backups(self):
        backups = glob.glob(os.path.join(self.target_path, '????-??-??_??????_incomplete'))
        return [name[len(self.target_path)+len(os.sep):] for name in backups]

    def find_latest_backup(self):
        """Locate the last backup. It is used as reference"""
        backups = self.find_backups()
        if backups:
            backups.sort()
            self.last_backup_path = os.path.join(self.target_path, backups[-1])
            logging.debug('Latest backup: %s' % (self.last_backup_path,))
        else:
            logging.info('No previous backup found')

    def load_configurations(self, file_list):
        c = BackupControl(self)
        for filename in file_list:
            c.load_file(filename)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class BackupControl(config_file_parser.ContolFileParser):
    """Parser for backup control files"""

    def word_target(self):
        self.backup.set_target_path(self.path(self.next_word()))

    def word_location(self):
        self.backup.source_locations.append(Location(self.path(self.next_word())))

    #~ def word_include(self):
    def word_exclude(self):
        self.backup.source_locations[-1].excludes.append(ShellPattern(self.next_word()))

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

    b = Backup()
    c = BackupControl(b)
    for filename in options.control:
        try:
            c.load_file(filename)
        except IOError as e:
            sys.stderr.write('Failed to load config: %s\n' % (e,))
            sys.exit(1)

    try:
        b.create(options.force)
    except BackupException as e:
        sys.stderr.write('ERROR: %s\n' % (e))
        sys.exit(1)


if __name__ == '__main__':
    main()
