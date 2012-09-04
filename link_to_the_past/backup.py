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
    if exp:
        return '%.1f%sB' % (value, EXPONENTS[exp])
    else:
        return '%dB' % (value,)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class BackupException(Exception):
    """A class for backup related errors"""

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def mode_to_chars(mode):
    """ls like mode as character sequence"""
    flags = []
    # file type
    if stat.S_ISDIR(mode):
        flags.append('d')
    elif stat.S_ISCHR(mode):
        flags.append('c')
    elif stat.S_ISBLK(mode):
        flags.append('b')
    elif stat.S_ISREG(mode):
        flags.append('-')
    elif stat.S_ISFIFO(mode):
        flags.append('p')
    elif stat.S_ISLNK(mode):
        flags.append('l')
    elif stat.S_ISSOCK(mode):
        flags.append('s')
    else:
        flags.append('?')
    # user permissions
    flags.append('r' if (mode & stat.S_IRUSR) else '-')
    flags.append('w' if (mode & stat.S_IWUSR) else '-')
    if mode & stat.S_ISUID:
        flags.append('s' if (mode & stat.S_IXUSR) else 'S')
    else:
        flags.append('x' if (mode & stat.S_IXUSR) else '-')
    # group permissions
    flags.append('r' if (mode & stat.S_IRGRP) else '-')
    flags.append('w' if (mode & stat.S_IWGRP) else '-')
    if mode & stat.S_ISGID:
        flags.append('s' if (mode & stat.S_IXGRP) else 'S')
    else:
        flags.append('x' if (mode & stat.S_IXGRP) else '-')
    # others permissions
    flags.append('r' if (mode & stat.S_IROTH) else '-')
    flags.append('w' if (mode & stat.S_IWOTH) else '-')
    if mode & stat.S_ISGID:
        flags.append('s' if (mode & stat.S_IXGRP) else 'S')
    elif mode & stat.S_ISVTX:
        flags.append('T' if (mode & stat.S_IXOTH) else 't')
    else:
        flags.append('x' if (mode & stat.S_IXOTH) else '-')
    # XXX alternate access character omitted

    return ''.join(flags)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class BackupPath(object):
    """Representing an object that is contained in the backup"""
    __slots__ = ['path', 'backup', 'changed', 'st_size', 'st_mode', 'st_uid',
                 'st_gid', 'st_atime', 'st_mtime', 'st_flags']

    def __init__(self, path=None):
        self.path = path
        self.backup = None
        self.st_size = 0
        self.st_uid = None
        self.st_gid = None
        self.st_mode = None
        self.st_mtime = None
        self.st_atime = None
        self.st_flags = None
        if path is not None:
            stat_now = os.lstat(path)
            self.st_size = stat_now.st_size
            self.st_uid = stat_now.st_uid
            self.st_gid = stat_now.st_gid
            self.st_mode = stat_now.st_mode
            self.st_mtime = stat_now.st_mtime
            self.st_atime = stat_now.st_atime
            if hasattr(stat_now, 'st_flags'):
                self.st_flags = stat_now.st_flags
        self.changed = False
        # XXX track changes of contents and meta data separately?

    @property
    def size(self):
        return self.st_size

    @property
    def abs_path(self):
        """Return absolute and full path to file within the current backup"""
        return self.join(self.backup.current_backup_path, self.path)

    def __str__(self):
        return '%s %s %s %6s %s %s' % (
                mode_to_chars(self.st_mode),
                self.st_uid,
                self.st_gid,
                nice_bytes(self.st_size),
                time.strftime('%Y-%m-%d %02H:%02M:%02S', time.localtime(self.st_mtime)),
                self.path)

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

    def set_stat(self, path, make_readonly=False):
        """\
        Apply all stat info (mode bits, atime, mtime, flags) to path.
        Optionally make it read-only.
        """
        if hasattr(os, 'utime'):
            os.utime(path, (self.st_atime, self.st_mtime))
        if hasattr(os, 'chmod'):
            mode = self.st_mode
            if make_readonly:
                mode &= ~(stat.S_IWUSR|stat.S_IWGRP|stat.S_IWOTH)
            os.chmod(path, mode)
        if hasattr(os, 'chflags'):
            try:
                os.chflags(path, self.st_flags)
            except OSError as why:
                if (not hasattr(errno, 'EOPNOTSUPP') or
                    why.errno != errno.EOPNOTSUPP):
                    raise
    @property
    def file_list_command(self):
        return 'p1 %s %s %s %s %.6f %.6f %s %s\n' % (
                self.st_mode,
                self.st_uid,
                self.st_gid,
                self.st_size,
                self.st_atime,
                self.st_mtime,
                self.st_flags if self.st_flags is not None else '-',
                self.escaped(self.path))


class BackupFile(BackupPath):
    """Information about a file as well as operations"""
    __slots__ = []

    def check_changes(self):
        """Compare the original file with the backup"""
        prev = os.lstat(os.path.join(self.backup.last_backup_path, self.path))
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
            shutil.copy(self.path, dst)
            self.set_stat(dst, make_readonly=True)
        # XXX make read-only

    def link(self):
        """Create a hard link for the file"""
        logging.debug('hard linking %s' % (self.escaped(self.path),))
        src = self.join(self.backup.last_backup_path, self.path)
        dst = self.join(self.backup.current_backup_path, self.path)
        os.link(src, dst)
        self.set_stat(dst, make_readonly=True)

    def create(self):
        """Backup the file, either by hard linking or copying"""
        if self.changed:
            self.copy()
        else:
            self.link()

    def secure(self):
        """Secure backup against manipulation (make read-only)"""
        # nothing to do here as that was already done when creating
        # the copy

    def restore(self, dst):
        """Create a copy of the file"""
        logging.debug('copying %s' % (self.escaped(self.path),))
        src = self.join(self.backup.current_backup_path, self.path)
        if os.path.islink(src):
            linkto = os.readlink(src)
            os.symlink(linkto, dst)
        else:
            # copy and apply mode, flags, mtime etc
            shutil.copy(src, dst)
            self.set_stat(dst)


class BackupDirectory(BackupPath):
    """Information about a directory as well as operations"""

    def __init__(self, *args, **kwargs):
        BackupPath.__init__(self, *args, **kwargs)
        self.st_size = 0    # file system may report != 0 but we're not interested in that

    def check_changes(self):
        """Directories are always created"""
        self.changed = True

    def create(self):
        """Directories are always created"""
        logging.debug('new directory %s' % (self.path,))
        os.makedirs(self.abs_path)
        # directory needs to stay writeable as we need to add files

    def secure(self):
        """Secure backup against manipulation (make read-only)"""
        self.set_stat(self.abs_path, make_readonly=True)

    def restore(self, dst):
        """Directories are always created"""
        logging.debug('new directory %s' % (self.path,))
        src = self.join(self.backup.current_backup_path, self.path)
        os.makedirs(dst)
        self.set_stat(dst)

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
        """Set the path to the backups (a directory)"""
        self.target_path = os.path.normpath(path)

    def find_backups(self):
        """Return a list of names, of complete backups"""
        backups = glob.glob(os.path.join(self.target_path, '????-??-??_??????'))
        return [name[len(self.target_path)+len(os.sep):] for name in backups]

    def find_incomplete_backups(self):
        """Return a list of names, of incomplete backups"""
        backups = glob.glob(os.path.join(self.target_path, '????-??-??_??????_incomplete'))
        return [name[len(self.target_path)+len(os.sep):] for name in backups]

    def find_latest_backup(self):
        """Locate the last backup. It is used as reference"""
        backups = self.find_backups()
        if backups:
            backups.sort()
            self.last_backup_path = os.path.join(self.target_path, backups[-1])
            logging.debug('Latest backup: %s' % (self.last_backup_path,))
            return backups[-1]
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

if __name__ == '__main__':
    import doctest
    doctest.testmod()
