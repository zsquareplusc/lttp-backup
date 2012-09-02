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
    __slots__ = ['path', 'backup', 'changed', 'stat_now']
    def __init__(self, path):
        self.path = path
        self.backup = None
        self.stat_now = os.lstat(self.path)
        self.changed = False
        # XXX track changes of contents and meta data separately?

    @property
    def size(self):
        return self.stat_now.st_size

    def __str__(self):
        return self.path

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.path)

    def join(self, root, path):
        return os.path.normpath('%s%s%s' % (root, os.sep, path))

    def escaped(self, path):
        return path.replace(' ', '\x20')    # XXX escape all control chars


class BackupFile(BackupPath):
    """Information about a file as well as operations"""
    __slots__ = []

    def check_changes(self):
        """Compare the original file with the backup"""
        prev = os.stat(os.path.join(self.backup.last_backup_path, self.path))
        #~ if (    self.stat_now.st_mode != prev.st_mode or
                #~ self.stat_now.st_uid != prev.st_uid or
                #~ self.stat_now.st_gid != prev.st_gid or
                #~ self.stat_now.st_size != prev.st_size or
                #~ self.stat_now.st_mode != prev.st_mode or
                #~ abs(self.stat_now.st_mtime - prev.st_mtime) > 0.00001): # as it is a float...
        # ignore changes in meta data. just look at the contents
        if (self.stat_now.st_size != prev.st_size or
                abs(self.stat_now.st_mtime - prev.st_mtime) > 0.00001): # 10us; as it is a float...
            self.changed = True

    def copy(self):
        """Create a copy of the file"""
        logging.debug('copying %s' % (self.path,))
        dst = self.join(self.backup.current_backup_path, self.path)
        if os.path.islink(self.path):
            linkto = os.readlink(self.path)
            os.symlink(linkto, dst)
        else:
            shutil.copy2(self.path, dst)

    def link(self):
        """Create a hard link for the file"""
        logging.debug('hard linking %s' % (self.path,))
        os.link(
                self.join(self.backup.last_backup_path, self.path),
                self.join(self.backup.current_backup_path, self.path)
                )

    def create(self):
        """Backup the file, either by hard linking or copying"""
        if self.changed:
            self.copy()
        else:
            self.link()

    @property
    def file_list_command(self):
        return 'f %s %s %s %s %.6f %s\n' % (
                self.stat_now.st_mode,
                self.stat_now.st_uid,
                self.stat_now.st_gid,
                self.stat_now.st_size,
                self.stat_now.st_mtime,
                self.escaped(self.path))


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

    @property
    def file_list_command(self):
        return 'dir %s %s %s %.6f %s\n' % (
                self.stat_now.st_mode,
                self.stat_now.st_uid,
                self.stat_now.st_gid,
                self.stat_now.st_mtime,
                self.escaped(self.path))

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
    """Backup"""
    def __init__(self):
        self.source_locations = []
        self.target_path = None
        self.current_backup_path = None
        self.last_backup_path = None
        self.base_name = None
        self.enforce_new_backup = False
        self.saved_items = []
        self.bytes_required = 0
        self.file_list = None

    def set_target_path(self, path):
        self.target_path = os.path.normpath(path)

    def add(self, bpath):
        """Add a file or directory to the items that are backed up"""
        bpath.backup = self
        self.saved_items.append(bpath)

    def find_latest_backup(self):
        """Locate the last backup. It is used as reference"""
        backups = glob.glob(os.path.join(self.target_path, '????-??-??_??????'))
        if backups:
            backups.sort()
            self.last_backup_path = backups[-1]
            logging.debug('Latest backup: %s' % (self.last_backup_path,))
        else:
            logging.info('No previous backup found')

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
        # rename directory
        self.file_list.close()
        self.file_list = None
        os.rename(self.current_backup_path, self.base_name)

    def scan_last_backup(self):
        """Find all files in the last backup"""
        # first (or forced) -> full copy
        if self.last_backup_path is None:
            logging.info('create full copy of all items')
            for item in self.saved_items:
                item.changed = True
        else:
            logging.info('checking for changes')
            for item in self.saved_items:
                item.check_changes()
        # count bytes to backup
        self.bytes_required = 0
        for item in self.saved_items:
            if isinstance(item, BackupFile) and item.changed:
                self.bytes_required += item.size

    def scan_sources(self):
        """Find all files contained in the current backup"""
        for location in self.source_locations:
            location.scan(self)

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
        if t.f_favail < len(self.saved_items):
            raise BackupException('target file system will not allow to create that many files')

    def create(self):
        #~ self.read_config()
        # find files to backup
        self.scan_sources()
        # find latest backup to work incrementally
        if not self.enforce_new_backup:
            self.find_latest_backup()
        self.scan_last_backup()
        logging.info('need to copy %d bytes' % (self.bytes_required,))
        # check target
        self.check_target()
        #~ for p in self.saved_items:
            #~ print p
        # backup files
        self.prepare_target()
        for p in self.saved_items:
            p.create()
            self.file_list.write(p.file_list_command)
        self.finalize_target()
        logging.info('created %s' % (self.base_name,))

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
if __name__ == '__main__':
    import doctest
    doctest.testmod()

