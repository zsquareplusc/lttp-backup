#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""\
Link To The Past - a backup tool

Compare backups and sources.

(C) 2012 cliechti@gmx.net
"""

from restore import *
import filelist

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def print_changes(iterator, long_format):
    for root, dirs, files in iterator:
        # sort by name again
        entries = []
        entries.extend((entry, ' ') for entry in files.same)
        entries.extend((entry, 'M') for entry in files.changed)
        entries.extend((entry, 'A') for entry in files.added)
        entries.extend((entry, 'R') for entry in files.removed)
        entries.extend((entry, ' ') for entry in dirs.same)
        entries.extend((entry, 'A') for entry in dirs.added)
        entries.extend((entry, 'R') for entry in dirs.removed)
        entries.sort()
        for entry, status in entries:
            if long_format:
                sys.stdout.write('%s %s\n' % (status, entry))
            else:
                sys.stdout.write('%s %s\n' % (status, entry.path))
        for e1, e2 in zip(files.changed, files.changed_other):
            print "<--", e1
            print "-->", e2

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
IMPLEMENTED_ACTIONS = ['verify', 'integrity', 'changes']

def main():
    import optparse
    import sys

    b = Restore()
    parser = optparse.OptionParser(usage='%prog [options] ACTION [...]')
    b.optparse_populate(parser)

    group = optparse.OptionGroup(parser, 'Display Options')
    group.add_option("-l", "--long",
        dest = "long_format",
        help = "Show detailed file info",
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
        if action == 'integrity':
            # compare hashes in backup with saved file list
            for item in b.root.flattened():
                logging.debug('checking %s' % (item.path,))
                status = 'OK'
                if isinstance(item, filelist.BackupFile):
                    if os.path.exists(item.backup_path):
                        if not item.verify_hash(item.backup_path):
                            status = 'CORRUPTED'
                    else:
                        status = 'MISSING'
                elif isinstance(item, filelist.BackupDirectory):
                    if not os.path.isdir(item.backup_path):
                        status = 'MISSING'
                if status:
                    sys.stdout.write('%s %s\n' % (status, item.path))
        elif action == 'verify':
            # compare hashes in source with saved file list
            if args:
                path = os.sep + args[0]
            else:
                path = '*'
            # XXX search only looks at file list, so won't find files added to the source
            for item in b.root.flattened():
                if fnmatch.fnmatch(item.path, path):
                    if isinstance(item, filelist.BackupFile):
                        if os.path.exists(item.path):
                            status = 'S' if item.verify_stat(item.path) else 'm'
                            if not item.verify_hash(item.path):
                                status = 'M'
                        else:
                            status = 'D'
                        sys.stdout.write('%s %s\n' % (status, item))
        elif action == 'changes':
            # compare changes between two backups
            if not args:
                parser.error('Missing TIMESPEC of backup to compare')
            # XXX "now" as word to scan sources instead of laoding a backup
            other_backup = Restore()
            other_backup.target_path = b.target_path
            if args[0] == 'now':
                other_backup.scan_sources()
            else:
                other_backup.find_backup_by_time(args[0])
            if b.current_backup_path == other_backup.current_backup_path:
                parser.error('Both TIMESPECs point to the same backup')
            print_changes(b.root.compare(other_backup.root), options.long_format)
        else:
            parser.error('unknown ACTION: %r' % (action,))
    except KeyboardInterrupt:
        sys.stderr.write('\nAborted on user request.\n')
        sys.exit(1)
    except BackupException as e:
        if options.debug: raise
        sys.stderr.write('ERROR: %s\n' % (e))
        sys.exit(1)
    t_end = time.time()
    logging.info('Action took %.1f seconds' % ((t_end - t_start),))


if __name__ == '__main__':
    main()
