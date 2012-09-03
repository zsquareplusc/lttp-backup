#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""\
Link To The Past - a backup tool

Restore and insprection tool.

(C) 2012 cliechti@gmx.net
"""
import os
import fnmatch
import logging

import config_file_parser
from backup import *

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class FileList(config_file_parser.ContolFileParser):
    """Parser for file lists"""

    def word_f(self):
        """Parse file info"""
        entry = BackupFile()
        entry.st_mode = int(self.next_word())
        entry.st_uid = int(self.next_word())
        entry.st_gid = int(self.next_word())
        entry.st_size = int(self.next_word())
        entry.st_mtime = float(self.next_word())
        entry.path = entry.unescape(self.next_word())
        self.backup.files_in_backup.append(entry)

    def word_dir(self):
        """Parse directory info"""
        entry = BackupDirectory(None)
        entry.st_mode = int(self.next_word())
        entry.st_uid = int(self.next_word())
        entry.st_gid = int(self.next_word())
        entry.st_mtime = float(self.next_word())
        entry.path = entry.unescape(self.next_word())
        self.backup.files_in_backup.append(entry)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class Restore(Backup):
    def __init__(self):
        Backup.__init__(self)
        self.files_in_backup = []

    def load_file_list(self):
        logging.debug('Loading file list')
        f = FileList(self)
        f.load_file(os.path.join(self.current_backup_path, 'file_list'))

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def main():
    import optparse
    import sys

    parser = optparse.OptionParser(usage='%prog [options] ACTION [...]')

    parser.add_option("-c", "--control",
        dest = "control",
        help = "Load control file",
        metavar = 'FILE',
        default = [],
        action = 'append'
    )

    #~ parser.add_option("-f", "--force",
        #~ dest = "force",
        #~ help = "Enforce certain operations (e.g. making a backup even if there is no change)",
        #~ default = False,
        #~ action = 'store_true'
    #~ )

    parser.add_option("--debug",
        dest = "debug",
        help = "Show technical details",
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

    b = Restore()
    try:
        b.load_configurations(options.control)
    except IOError as e:
        sys.stderr.write('Failed to load configuration: %s\n' % (e,))
        sys.exit(1)

    if not args:
        parser.error('Expected ACTION')
    action = args.pop(0)

    try:
        if action == 'list':
            backups = b.find_backups()
            backups.sort()
            for name in backups:
                sys.stdout.write('%s\n' % (name,))
            bad_backups = b.find_incomplete_backups()
            if bad_backups:
                logging.warn('Incomplete %d backup(s) detected' % (len(bad_backups),))
        elif action == 'ls':
            b.find_latest_backup()
            b.current_backup_path = b.last_backup_path
            b.load_file_list()
            if args:
                path = os.sep + args[0]
            else:
                path = '*'
            for item in b.files_in_backup:
                if fnmatch.fnmatch(item.path, path):
                    sys.stdout.write('%s\n' % (item,))
        else:
            parser.error('unknown ACTION: %r' % (action,))
    except BackupException as e:
        sys.stderr.write('ERROR: %s\n' % (e))
        sys.exit(1)


if __name__ == '__main__':
    main()
