#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""\
Link To The Past - a backup tool

Compare backups and sources.

(C) 2012 cliechti@gmx.net
"""

from restore import *

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
IMPLEMENTED_ACTIONS = ['verify', 'integrity', 'changes']

def main():
    import optparse
    import sys

    b = Restore()
    parser = optparse.OptionParser(usage='%prog [options] ACTION [...]')
    b.optparse_populate(parser)

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
                status = None
                if isinstance(item, BackupFile):
                    if os.path.exists(item.abs_path):
                        if not item.verify_hash(item.abs_path):
                            status = 'CORRUPTED'
                    else:
                        status = 'MISSING'
                elif isinstance(item, BackupDirectory):
                    if not os.path.isdir(item.abs_path):
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
                    if isinstance(item, BackupFile):
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
            other_backup.includes = b.includes
            other_backup.excludes = b.excludes
            if args[0] == 'now':
                other_backup.scan_sources()
            else:
                other_backup.find_backup_by_time(args[0])
            if b.current_backup_path == other_backup.current_backup_path:
                parser.error('Both TIMESPECs point to the same backup')
            for src_dir in b.root.walk():
                try:
                    other_entry = other_backup.root[src_dir.path]
                except KeyError:
                    status = 'D'
                    sys.stdout.write('%s %s\n' % (status, src_dir.path))
                    if isinstance(src_dir, BackupDirectory):
                        for item in src_dir.flattened():
                            sys.stdout.write('%s %s\n' % (status, item.path))
                else:
                    ref = list(other_entry.entries) # work on copy
                    for entry in src_dir.entries:
                        for ref_entry in ref:
                            if entry.path == ref_entry.path:
                                if entry.st_mode == ref_entry.st_mode:  # XXX proper compare
                                    status = 'S'
                                else:
                                    status = 'm'
                                ref.remove(ref_entry)
                                break
                        else:
                            status = 'D'
                        sys.stdout.write('%s %s\n' % (status, entry.path))
                    # print files in ref but not in source
                    status = 'A'
                    for ref_entry in ref:
                        sys.stdout.write('%s %s\n' % (status, ref_entry.path))
                        if isinstance(ref_entry, BackupDirectory):
                            for item in ref_entry.flattened():
                                sys.stdout.write('%s %s\n' % (status, item.path))

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
