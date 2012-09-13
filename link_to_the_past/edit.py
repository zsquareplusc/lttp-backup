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

import shutil

from restore import *
from error import BackupException

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class writeable(object):
    """\
    Context manager that chmod's the given path to make it writeable.
    The original permissions are restored on exit.
    """
    def __init__(self, path):
        self.path = path
        self.permissions = os.lstat(path).st_mode

    def __enter__(self):
        os.chmod(self.path, self.permissions|stat.S_IWUSR)

    def __exit__(self, exc_type, exc_value, traceback):
        os.chmod(self.path, self.permissions)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class EditBackup(Restore):

    def write_file_list(self):
        """Write a new version of the file list"""
        with writeable(self.current_backup_path):
            self.root.save(os.path.join(self.current_backup_path, 'file_list'))

    def rm(self, source, recursive=False, force=False):
        """\
        Remove a file or a directory (if recursive flag is set).
        This will ultimately delete the file(s) from the backup!
        """
        item = self.root[source]
        if isinstance(item, filelist.BackupDirectory):
            if recursive:
                # parent temporarily needs to be writeable to remove files
                with writeable(item.parent.backup_path):
                    # make all sub-entries writable
                    for entry in item.flattened(include_self=True):
                        # directories need to be writeable
                        if isinstance(entry, filelist.BackupDirectory):
                            entry.stat.mode |= stat.S_IWUSR
                            entry.stat.write(entry.backup_path, chmod_only=True)
                    # then remove the complete sub-tree
                    shutil.rmtree(item.backup_path)
                item.parent.entries.remove(item)
            else:
                raise BackupException('will not work on directories in non-recursive mode: %r' % (filelist.escaped(source),))
        else:
            # parent temporarily needs to be writeable to remove files
            with writeable(item.parent.backup_path):
                #~ os.chmod(item.abs_path, stat.S_IWUSR|stat.S_IRUSR)
                try:
                    os.remove(item.backup_path)
                except OSError as e:
                    if force:
                        logging.warning('could not remove file: %s' % (e,))
                    else:
                        raise BackupException('could not remove file: %s' % (e,))
            item.parent.entries.remove(item)
        self.write_file_list()

    def purge(self):
        """Remove the entire backup"""
        # make the backup writeable
        os.chmod(self.current_backup_path, stat.S_IRUSR|stat.S_IWUSR|stat.S_IXUSR)
        # make all sub-directoris writable, needed for rmdir
        for path, dirs, files in self.root.walk():
            # directories need to be writeable
            for directory in dirs:
                directory.stat.mode |= stat.S_IWUSR
                directory.stat.write(directory.backup_path, chmod_only=True)
        # then remove the complete tree
        shutil.rmtree(self.current_backup_path)


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def ask_the_question():
    sys.stderr.write('This alters the backup. The file(s) will be lost forever!\n')
    if raw_input('Continue? [y/N] ').lower() != 'y':
        sys.stderr.write('Aborted\n')
        sys.exit(1)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
IMPLEMENTED_ACTIONS = ['rm']

def main():
    import optparse
    import sys

    b = EditBackup()
    parser = optparse.OptionParser(usage='%prog [options] ACTION [...]')
    b.optparse_populate(parser)

    group = optparse.OptionGroup(parser, 'File Selection')
    group.add_option("-f", "--force",
        dest = "force",
        help = "enforce certain operations",
        default = False,
        action = 'store_true'
    )
    group.add_option("-r", "--recursive",
        dest = "recursive",
        help = "apply operation recursively to all subdirectories",
        default = False,
        action = 'store_true'
    )
    parser.add_option_group(group)

    (options, args) = parser.parse_args(sys.argv[1:])

    b.optparse_evaluate(options)


    if not args:
        parser.error('Expected ACTION')
    action = args.pop(0)

    t_start = time.time()
    try:
        if action == 'rm':
            if len(args) != 1:
                parser.error('expected SRC')
            entry = b.root[args[0]] # XXX just test if it is there. catch ex and print error
            sys.stderr.write('Going to remove %s\n' % (filelist.escaped(entry.path),))
            ask_the_question()
            b.rm(args[0], options.recursive, options.force)
        elif action == 'purge':
            if args:
                parser.error('not expected any arguments')
            sys.stderr.write('Going to remove the entire backup: %s\n' % (os.path.basename(b.current_backup_path),))
            ask_the_question()
            b.purge()
        #~ elif action == 'autopurge':
        else:
            parser.error('unknown ACTION: %r' % (action,))
    except KeyboardInterrupt:
        sys.stderr.write('\nAborted on user request.\n')
        sys.exit(1)
    except (KeyError, BackupException) as e:
        sys.stderr.write('ERROR: %s\n' % (e))
        sys.exit(1)
    t_end = time.time()
    logging.info('Action took %.1f seconds' % ((t_end - t_start),))


if __name__ == '__main__':
    main()
