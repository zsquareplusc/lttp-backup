#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""\
Link To The Past - a backup tool

Command line front-end.

(C) 2012 cliechti@gmx.net
"""

import sys
import optparse

import link_to_the_past
from link_to_the_past import config_file_parser

import glob
import os

def main():
    import logging

    parser = optparse.OptionParser(usage='%prog [options] ACTION [...]')

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

    b = link_to_the_past.Backup()
    c = config_file_parser.BackupControl(b)
    for filename in options.control:
        try:
            c.load_file(filename)
        except IOError as e:
            sys.stderr.write('Failed to load config: %s\n' % (e,))
            sys.exit(1)

    if not args:
        parser.error('Expected ACTION')
    action = args.pop(0)

    try:
        if action == 'backup':
            b.create(options.force)
        elif action == 'list':
            backups = glob.glob(os.path.join(b.target_path, '????-??-??_??????'))
            for name in backups:
                sys.stdout.write('%s\n' % (name[len(b.target_path)+len(os.sep):],))
            bad_backups = glob.glob(os.path.join(b.target_path, '????-??-??_??????_incomplete'))
            if bad_backups:
                logging.warn('Incomplete %d backup(s) detected' % (len(bad_backups),))
        elif action == 'ls':
            b.find_latest_backup()
            path = b.last_backup_path
            if args:
                path += os.sep + args[0]
            print os.listdir(path)
        elif action == 'test':
            print b
            print "Target:", b.target_path
            print "Sources:", b.source_locations
            print "Excludes (1):", b.source_locations[-1].excludes
        else:
            parser.error('unknown ACTION: %r' % (action,))
    except link_to_the_past.BackupException as e:
        sys.stderr.write('ERROR: %s\n' % (e))
        sys.exit(1)


if __name__ == '__main__':
    main()
