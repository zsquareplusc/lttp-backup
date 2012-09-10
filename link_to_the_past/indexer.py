#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""\
Link To The Past - a backup tool

Scan file system to create file lists.

(C) 2012 cliechti@gmx.net
"""
import sys
import os
import fnmatch
import stat
import logging

import filelist
from error import BackupException

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
        self.path = os.path.normpath(os.path.abspath(path))
        self.excludes = []

    def __repr__(self):
        return 'Location(%r)' % (self.path,)

    def _scan(self, indexer, parent, device):
        """scan recursively and handle excluded files on the fly"""
        logging.debug('scanning %r' % (parent.path,))
        for name in os.listdir(unicode(parent.path)):
            if isinstance(name, str):
                logging.error('encoding error in filename, name in backup is altered!: %r' % (name,))
                name = name.decode('utf-8', 'ignore')   # XXX
            path = os.path.join(parent.path, name)
            if indexer.is_included(path):
                #~ logging.debug('is included %r' % (path,))
                try:
                    stat_now = os.lstat(path)
                except OSError: # permission error
                    logging.error('access failed, ignoring: %s' % (path,))
                    continue
                # do not cross filesystem boundaries
                if stat_now.st_dev != device:
                    logging.warning('will not cross filesystems, ignore: %r' % (path,))
                    continue
                # store dirs and files
                mode = stat_now.st_mode
                if stat.S_ISDIR(mode):
                    d = parent.new_dir(name, stat_now=stat_now)
                    self._scan(indexer, d, device)
                elif stat.S_ISREG(mode) or stat.S_ISLNK(mode):
                    parent.new_file(name, stat_now=stat_now)
                #~ elif stat.S_ISCHR(mode):
                #~ elif stat.S_ISBLK(mode):
                #~ elif stat.S_ISFIFO(mode):
                #~ elif stat.S_ISSOCK(mode):
                #~ else:
                    # ignore everything else
            #~ else:
                #~ logging.debug('is excluded %r' % (path,))

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
            raise BackupException('location is not a directory: %r' % (self.path,))


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
        print entry

    #~ import doctest
    #~ doctest.testmod()

