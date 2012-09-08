#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""\
Link To The Past - a backup tool

Manage file lists.

(C) 2012 cliechti@gmx.net


A file list references two points.
- an absolute path. this is usually the "original" file (source_path)
- a relative path to some other root. typically the root is a backup. (backup_path)

When creating a backup, also a third location is relevant; the previous backup.

Operations affecting the file system:
- cp (backup_path -> destination of choice)
- backup (create backup_path either by hard linking to previous_backup_path or copying source_path)
"""
import sys
import os
import time
import fnmatch
import stat
import logging

import config_file_parser
import hashes

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
EXPONENTS = ('', 'k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')

def nice_bytes(value):
    """\
    Return a string for a number representing bytes in a human readable form
    (1kB=1000B as usual for storage devices now days).

    >>> nice_bytes(1024)
    '1.0kB'
    >>> nice_bytes(2e9)
    '2.0GB'
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

def mode_to_chars(mode):
    """'ls' like mode as character sequence"""
    if mode is None: return '----------'
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

def escaped(path):
    """Escape control non printable characters and the space"""
    return path.encode('unicode-escape').replace(' ', '\\ ')

def unescape(path):
    """Escape control non printable characters and the space"""
    return path.decode('unicode-escape').replace('\\ ', ' ')

#~ def join(root, path):
    #~ return os.path.normpath('%s%s%s' % (root, os.sep, path))

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class Stat(object):
    """Handle file meta data"""
    __slots__ = ['size', 'mode', 'uid', 'gid', 'atime', 'mtime', 'flags']
    def __init__(self):
        self.size = 0
        self.uid = None
        self.gid = None
        self.mode = None
        self.mtime = None
        self.atime = None
        self.flags = None

    def extract(self, stat_now):
        if stat.S_ISDIR(stat_now.st_mode):
            self.size = 0
        else:
            self.size = stat_now.st_size
        self.uid = stat_now.st_uid
        self.gid = stat_now.st_gid
        self.mode = stat_now.st_mode
        self.mtime = stat_now.st_mtime
        self.atime = stat_now.st_atime
        if hasattr(stat_now, 'st_flags'):
            self.flags = stat_now.st_flags
        else:
            self.flags = None

    def write(self, path):
        """\
        Apply all stat info (mode bits, atime, mtime, flags) to path.
        Only useful when called on files but not on symlinks (links are ignored).
        """
        if stat.S_ISLNK(self.st_mode):
            pass
            # XXX should have l-versions of all functions - missing in Python os mod. :(
            #~ os.lutime(dst, (self.st_atime, self.st_mtime))   # XXX missing in os module!
            #~ os.system('touch --no-dereference -r "%s" "%s"' % (self.escaped(self.path), self.escaped(dst))) # XXX insecure!
        else:
            os.utime(path, (self.atime, self.mtime))
            os.chown(path, self.uid, self.gid)
            if hasattr(os, 'chflags'):
                try:
                    os.chflags(path, self.flags)
                except OSError as why:
                    if (not hasattr(errno, 'EOPNOTSUPP') or
                        why.errno != errno.EOPNOTSUPP):
                        raise
            os.chmod(path, self.mode)

    def make_read_only(self, path):
        """use chmod to apply the modes with W bits cleared"""
        # XXX should have l-versions of all functions - missing in Python os mod. :(
        if not stat.S_ISLNK(self.mode):
            os.chmod(path, self.mode & ~(stat.S_IWUSR|stat.S_IWGRP|stat.S_IWOTH))

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class BackupPath(object):
    """Representing an object that is contained in the backup"""
    __slots__ = ['name', 'parent', '_path', 'filelist', 'changed', 'data_hash', 'stat']

    def __init__(self, name=None, filelist=None, stat_now=None, parent=None):
        self.name = name
        self.parent = parent
        self._path = None
        self.stat = Stat()
        self.data_hash = '-'
        self.filelist = filelist
        if stat_now is not None:
            self.stat.extract(stat_now)
        self.changed = True

    @property
    def path(self):
        """Return full path. Once calculated, cache it"""
        if self._path is None:
            if self.parent is not None:
                self._path = os.path.join(self.parent.path, self.name)
            else:
                self._path = self.name
        return self._path

    @property
    def backup_path(self):
        """Return absolute path to file relative to the root"""
        return os.path.normpath(join(self.filelist.root, self.path))

    @property
    def source_path(self):
        """Return absolute and full path to file"""
        return self.path

    @property
    def referece_path(self):
        """Return absolute path to file relative to the reference"""
        return os.path.normpath(join(self.filelist.reference, self.path))

    def __str__(self):
        return '%s %4s %4s %6s %s %s' % (
                mode_to_chars(self.stat.mode),
                self.stat.uid,
                self.stat.gid,
                nice_bytes(self.stat.size),
                time.strftime('%Y-%m-%d %02H:%02M:%02S', time.localtime(self.stat.mtime)),
                self.path)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.path)

    @property
    def file_list_command(self):
        return 'p1 %s %s %s %s %.9f %.9f %s %s %s\n' % (
                self.stat.mode,
                self.stat.uid,
                self.stat.gid,
                self.stat.size,
                self.stat.atime,
                self.stat.mtime,
                self.stat.flags if self.stat.flags is not None else '-',
                self.data_hash,
                self.escaped(self.path))


class BackupFile(BackupPath):
    """Information about a file as well as operations"""

    BLOCKSIZE = 1024*256   # 256kB

    #~ def check_changes(self):
        #~ """Compare the original file with the backup"""
        #~ try:
            #~ prev = os.lstat(self.join(self.backup.last_backup_path, self.path))
        #~ except OSError:
            #~ # file does not exist in backup
            #~ self.changed = True
        #~ else:
            #~ # ignore changes in other meta data. just look at the size and mtime
            #~ if (self.st_size == prev.st_size and
                    #~ abs(self.st_mtime - prev.st_mtime) <= 0.00001): # 10us; as it is a float...
                #~ self.changed = False

    def cp(self, dst, permissions=True):
        """\
        Create a copy of the file (or link) to given destination. Permissions
        are restored if the flag is true.
        """
        logging.debug('copying %s' % (escaped(self.path),))
        hexdigest = self._copy_file(self.backup_path, dst)
        if permissions:
            self.stat.write(dst)
        if self.data_hash != hexdigest:
            logging.error('ERROR: hash changed! File was copied successfully but does not match the stored hash: %s' % (escape(self.path),))

    def _copy_file(self, src, dst):
        """Create a copy a file (or link)"""
        h = self.backup.hash_factory()
        if os.path.islink(src):
            linkto = os.readlink(src)
            h.update(linkto)
            os.symlink(linkto, dst)
        else:
            with open(src, 'rb') as f_src:
                with open(dst, 'wb') as f_dst:
                    while True:
                        block = f_src.read(self.BLOCKSIZE)
                        if not block:
                            break
                        h.update(block)
                        f_dst.write(block)
        return h.hexdigest()

    def _copy(self, src, dst):
        """Create a copy of the file"""
        self.data_hash = self._copy_file(self.referece_path, self.backup_path)
        os.utime(dst, (self.st_atime, self.st_mtime))
        self.make_read_only(self.backup_path)

    def _link(self):
        """Create a hard link for the file"""
        logging.debug('hard linking %s' % (escaped(self.path),))
        os.link(self.referece_path, self.backup_path)
        self.make_read_only(self.backup_path)

    def create(self):
        """Backup the file, either by hard linking or copying"""
        if self.changed:
            self._copy()
        else:
            self._link()

    def secure_backup(self):
        """Secure backup against manipulation (make read-only)"""
        # nothing to do here as that was already done when creating
        # the backup

    def verify_hash(self, path):
        """\
        Compare given path by calculating the hash over the data.
        Returns true when the calculated hash matches the stored one.
        """
        h = self.filelist.hash_factory()
        if os.path.islink(path):
            h.update(os.readlink(path))
        else:
            with open(path, 'rb') as f_src:
                while True:
                    block = f_src.read(self.BLOCKSIZE)
                    if not block:
                        break
                    h.update(block)
        return self.data_hash == h.hexdigest()

    def verify_stat(self, path):
        """\
        Compare given path's meta data with the stored one. Return true if they
        are the same.
        Note: st_atime is not checked.
        """
        stat_now = os.lstat(path)
        if stat.S_ISDIR(stat_now.st_mode):
            st_size = 0
        else:
            st_size = stat_now.st_size
        if hasattr(stat_now, 'st_flags'):
            st_flags = stat_now.st_flags
        else:
            st_flags = None
        return (self.stat.uid == stat_now.st_uid and
                self.stat.gid == stat_now.st_gid and
                self.stat.mode == stat_now.st_mode and
                self.stat.size == st_size and
                abs(self.stat.mtime - stat_now.st_mtime) <= 0.00001 and # 10us; as it is a float...
                self.stat.flags == st_flags)


class BackupDirectory(BackupPath):
    """Information about a directory as well as operations"""
    __slots__ = ['entries']

    def __init__(self, *args, **kwargs):
        BackupPath.__init__(self, *args, **kwargs)
        self.entries = []

    #~ def check_changes(self):
        #~ """Directories are always created"""
        #~ self.changed = True

    def create(self):
        """Directories are always created"""
        logging.debug('new directory %s' % (escape(self.path),))
        os.makedirs(self.abs_path)
        os.utime(self.abs_path, (self.st_atime, self.st_mtime))
        # directory needs to stay writeable as we need to add files

    def secure_backup(self):
        """Secure backup against manipulation (make read-only)"""
        self.make_read_only(self.backup_path)

    def cp(self, dst, permissions=True, recursive=False):
        """Copy directories to given destination"""
        logging.debug('new directory %s' % (escape(self.path),))
        os.makedirs(dst)
        if recursive:
            for entry in self.entries:
                if isinstance(entry, BackupDirectory):
                    entry.cp(os.path.join(dst, entry.name), permissions=permissions, recursive=True)
                else:
                    entry.cp(os.path.join(dst, entry.name), permissions=permissions)
        if permissions:
            # set permission as last step in case a directory is made read-only
            self.set_stat(dst)

    def flattened(self, include_self=False):
        """Generator yielding all directories and files recursively"""
        if include_self:
            yield self
        for entry in self.entries:
            yield entry
            if isinstance(entry, BackupDirectory):
                for x in entry.flattened():
                    yield x

    #~ def files(self):
        #~ """Iterate over files in a directory, subdirectories are ignored"""
        #~ for entry in self.entries:
            #~ if isinstance(entry, BackupFile):
                #~ yield entry

    def walk(self):
        """Generator yielding all directories recursively"""
        yield self
        for entry in self.entries:
            if isinstance(entry, BackupDirectory):
                for x in entry.walk():
                    yield x

    def __getitem__(self, name):
        if os.sep in name:
            head, tail = name.split(os.sep, 1)
            for entry in self.entries:
                if entry.name == head:
                    return entry[tail]  # XXX only if dir
        else:
            for entry in self.entries:
                if entry.name == name:
                    return entry
        raise KeyError('no such directory: %s' % (name,))

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class FileList(BackupDirectory):
    """Manage a tree of files and directories."""
    def __init__(self):
        BackupDirectory.__init__(self, '/')
        self.root = None
        self.reference = None
        self.base_name = None
        self.hash_name = None

    def set_hash(self, name):
        if name is None:
            self.hash_factory = None
        else:
            self.hash_factory = hashes.get_factory(name)
        self.hash_name = name

    def load(self, filename):
        logging.debug('Loading file list %s' % (filename,))
        c = FileListParser(self)
        c.load_file(filename)

    def __getitem__(self, name):
        if name == self.name:
            return self
        if name.startswith(self.name):
            name = name[len(self.name):]
            return BackupDirectory.__getitem__(self, name)
        raise KeyError('no such directory: %s' % (name,))


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class FileListParser(config_file_parser.ContolFileParser):
    """Parser for file lists."""

    def __init__(self, filelist):
        config_file_parser.ContolFileParser.__init__(self)
        self.filelist = filelist
        self.filelist.set_hash(None)

    def word_hash(self):
        """Set the hash function"""
        if self.filelist.hash_name is not None:
            logging.warn('HASH directive found multiple times')
        self.filelist.set_hash(self.next_word())

    def word_p1(self):
        """Parse file info and add it to the internal (file) tree"""
        st_mode = int(self.next_word())
        if stat.S_ISDIR(st_mode):
            entry = BackupDirectory(filelist=self.filelist)
        else:
            entry = BackupFile(filelist=self.filelist)
        entry.stat.mode = st_mode
        entry.stat.uid = int(self.next_word())
        entry.stat.gid = int(self.next_word())
        entry.stat.size = int(self.next_word())
        entry.stat.atime = float(self.next_word())
        entry.stat.mtime = float(self.next_word())
        st_flags = self.next_word()
        if st_flags != '-':
            entry.stat.flags = float(st_flags)
        entry.data_hash = self.next_word()
        path = unescape(self.next_word())
        path, entry.name = os.path.split(path)
        entry.parent = self.filelist[path]
        entry.parent.entries.append(entry)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

if __name__ == '__main__':
    f = FileList()
    f.load('test/example_backups/2012-09-07_043453/file_list')
    for entry in f.flattened():
        print entry

    import doctest
    doctest.testmod()
