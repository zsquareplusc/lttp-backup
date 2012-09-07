#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""\
Link To The Past - a backup tool

Compare backups and sources.

(C) 2012 cliechti@gmx.net
"""

from restore import *

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
IMPLEMENTED_ACTIONS = ['verify']

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
        if action == 'verify':
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
        else:
            parser.error('unknown ACTION: %r' % (action,))
    except KeyboardInterrupt:
        sys.stderr.write('\nAborted on user request.\n')
        sys.exit(1)
    except BackupException as e:
        sys.stderr.write('ERROR: %s\n' % (e))
        sys.exit(1)
    t_end = time.time()
    logging.info('Action took %.1f seconds' % ((t_end - t_start),))


if __name__ == '__main__':
    main()
