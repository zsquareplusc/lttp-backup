#!/usr/bin/env python3
# encoding: utf-8
#
# (C) 2012-2016 Chris Liechti <cliechti@gmx.net>
#
# SPDX-License-Identifier:    BSD-3-Clause
"""\
Link To The Past - a backup tool

Scan file system to create file lists.
"""
import os
import fnmatch
import stat
import logging

from . import filelist
from .error import BackupException


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class ShellPattern(object):
    """A shell like pattern to test filenames"""
    def __init__(self, pattern):
        self.pattern = pattern

    def __repr__(self):
        return 'ShellPattern({!r})'.format(self.pattern)

    def matches(self, filename):
        return fnmatch.fnmatch(filename, self.pattern)


class Location(object):
    """A location on the file system, used as source for backups"""
    def __init__(self, path):
        self.path = os.path.normpath(os.path.abspath(path))
        self.excludes = []

    def __repr__(self):
        return 'Location({!r})'.format(self.path)

    def _scan(self, indexer, parent, device):
        """scan recursively and handle excluded files and directories on the fly"""
        logging.debug('scanning {!r}'.format(parent.path))
        for direntry in os.scandir(parent.path):
            if indexer.is_included(direntry.path):
                #~ logging.debug('is included %r' % (direntry.path,))
                try:
                    stat_now = direntry.stat(follow_symlinks=False)
                except OSError:  # permission error
                    logging.error('access failed, ignoring: {!r}'.format(direntry.path))
                    continue
                # do not cross filesystem boundaries
                if stat_now.st_dev != device:
                    logging.warning('will not cross filesystems, ignoring: {!r}'.format(direntry.path))
                    continue
                # store dirs and files
                mode = stat_now.st_mode
                if stat.S_ISDIR(mode):
                    d = parent.new_dir(direntry.name, stat_now=stat_now)
                    self._scan(indexer, d, device)
                elif stat.S_ISREG(mode) or stat.S_ISLNK(mode):
                    parent.new_file(direntry.name, stat_now=stat_now)
                #~ elif stat.S_ISCHR(mode):
                #~ elif stat.S_ISBLK(mode):
                #~ elif stat.S_ISFIFO(mode):
                #~ elif stat.S_ISSOCK(mode):
                #~ else:
                    # ignore everything else
            #~ else:
                #~ logging.debug('is excluded %r' % (direntry.path,))

    def scan(self, indexer):
        """Find all files in the source directory"""
        path = os.path.abspath(self.path)
        if os.path.isdir(path):
            parents = path.split(os.sep)
            del parents[0]  # remove empty root
            parent = indexer.root
            for name in parents:
                entry = parent.new_dir(name)
                entry.stat.extract(os.lstat(entry.path))
                parent = entry
            self._scan(indexer, parent, os.lstat(path).st_dev)
        else:
            raise BackupException('location is not a directory: {!r}'.format(self.path))


class Indexer(object):
    """Manage a tree of files and directories."""
    def __init__(self, filelist):
        self.includes = []
        self.excludes = []
        self.root = filelist

    def is_included(self, name):
        for exclude in self.excludes:
            if exclude.matches(name):
                return False
        return True

    def scan(self):
        """Find all files contained in the current backup"""
        for location in self.includes:
            location.scan(self)


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
if __name__ == '__main__':
    i = Indexer(filelist.FileList())
    i.includes.append(Location('test/example_source'))
    i.excludes.append(ShellPattern('*.bak'))
    i.scan()
    for entry in i.root.flattened():
        print(entry)

    #~ import doctest
    #~ doctest.testmod()
