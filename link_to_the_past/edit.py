#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""\
Link To The Past - a backup tool

Modify backups.

Sometimes it is even useful to edit backups. E.g. to remove files or
directories that have been archived by accident.

Actions to delete backups are also here. A specific backup can be
deleted and there is an automatic delete function that keeps less
backups the further back in time they were made.

(C) 2012 cliechti@gmx.net
"""

from restore import *

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class EditBackup(Restore):

    def rm(self, source, recursive=False):
        """\
        Remove a file or a directory (if recursive flag is set).
        This will ultimately delete the file(s) from the backup!
        """
        item = self.find_file(source)
        if isinstance(item, BackupDirectory):
            if recursive:
                # parent temporarily needs to be writeable to remove files
                with writeable(item.parent.abs_path):
                    # make all sub-entries writable
                    for entry in item.flattened(include_self=True):
                        # directories need to be writeable
                        if isinstance(entry, BackupDirectory):
                            entry.st_mode |= stat.S_IWUSR
                            entry.set_stat(entry.abs_path)
                    # then remove the complete sub-tree
                    shutil.rmtree(item.abs_path)
                item.parent.entries.remove(item)
            else:
                raise BackupException('will not work on directories in non-recursive mode: %r' % (source,))
        else:
            # parent temporarily needs to be writeable to remove files
            with writeable(item.parent.abs_path):
                #~ os.chmod(item.abs_path, stat.S_IWUSR|stat.S_IRUSR)
                os.remove(item.abs_path)
            item.parent.entries.remove(item)
        self.write_file_list()

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
IMPLEMENTED_ACTIONS = ['rm']

def main():
    import optparse
    import sys

    b = EditBackup()
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
        if action == 'rm':
            if len(args) != 1:
                parser.error('expected SRC')
            b.find_file(args[0]) # XXX just test if it is there
            sys.stderr.write('This alters the backup. The file(s) will be lost forever!\n')
            if raw_input('Continue? [y/N]').lower() != 'y':
                sys.stderr.write('Aborted\n')
                sys.exit(1)
            b.rm(args[0], options.recursive)
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
