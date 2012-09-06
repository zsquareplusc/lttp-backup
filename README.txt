==================
 Link to the past
==================

Simple backup program.

- Works incrementally while providing full backups at any time. Use hard links
  to reference files from the previous backup, so each backup looks like a
  full backup. While saving space on all the files that have not changed.

- Check before doing. Available space and capability to create the required
  number of files is checked before the copying starts.

- Does not rely on external tools (cp, rsync etc).

- Does not erase failed backup. It's your decision to delete these.

Yes it not the first program of that kind. The reason it exists is that
existing programs did not work well with some files or amount of data.
There is no need to use rsync to make local copies. Analyzing the files takes
more time than simply copying it.


The backup is always a simple copy of the files. This ensures that the backup
can be used in any point in the future. Even if the backup program is lost or
incompatible.


- Changed files are copied entirely.
- Special files (devices) are not backed up.
- XXX do not cross file systems
- Files are checked by modification date and size.
- Backups are timestamped, you can not create more than one backup per second
  :-)
- Hard linked files only exist once on the disk. This is also a risk that when
  it is damaged (disk errors, user manipulations), then the references in all
  backups are also damages. To safeguard against this risk, create full
  copies form time to time and/or use different disks to backup.
- The target location needs to be in the file system. This tool does not
  support backing up via protocols like ssh, ftp etc. Typically the target
  will be a USB disk or memory stick but it also works well with storage in
  the network, e.g. a NAS mounted via NFS.
- Time stamps are stored in microsecond resolution (some file systems allow
  higher accuracy, if this is need by the application, do not use this backup
  tool). Change detection works at a resolution of 10µs (this should not be a
  problem as making a backup certainly takes longer than that).


Command Line Tool
=================

general options:
    -v                  make outputs more verbose, can be given multiple times
    -q                  switch off messages
    --debug             for the programmer: shows tracebacks for failures
    -c CONFIGURATION    load given configuration file
    -p PROFILENAME      load given profile. profiles are configuration files
                        in ``~/.link_to_the_past``.

Create Backups
--------------
python -m link_to_the_past.create -c CONFIGURATION

options:
    --full              copy all items, do not depend on last backup.
    -f, --force         create backup anyway, even if no files have changed

Restore Files
-------------
python -m link_to_the_past.restore -c CONFIGURATION ACTION [...]

options:
    -c CONFIGURATION    load given configuration file
    -t TIMESPEC         specify a backup, default (option not given, is to use
                        the latest backup)

actions:
    list                list all backups
    ls [PATTERN]        list files of backup, optionally filtered by PATTERN
    cp SRC DST          copy a single file from the backup (SRC) to DST
    cp -r SRC DST       copy a directory recursively from the backup (SRC) to DST
    cat SRC             dump single file from the backup (SRC) to stdout
    path                print the absolute path to the backup
    rm SRC              remove a file from the backup
    rm -r SRC           remove a directory and all its contents

Copy
----
The ``cp`` action copies files or directories from the backup to the given
destination. This is a convenient way to restore files in to a new location.

.. warning:: Existing a file or directory with the same name will be overwritten!


Remove
------
The ``rm`` action deletes files from the backup. Its purpose is to remove
items that have been accidentally backed up (e.g. temporary files, caches,
sensitive content etc.).

.. warning:: This destroys the files in the backup, use with extreme care!

.. note:: It usually makes sense to add an ``exclude`` rule to the
          control file so that it is not included again in the next backup.

Profiles
========
A profile is the same as a configuration file but located in a sepcial place.
The idea is to make it easier to work with multiple configurations.

Without any -p or -c options, a default configuration is searched.
1) A file named ``default.profile`` in the current directory
2) A file named ``default.profile`` in the users ``.link_to_the_past``
   directory

Named profiles are loaded with the ``-p <name>`` option. A file 
``<name>.profile`` is searched in the users ``.link_to_the_past``
directory.


Configuration file format
=========================
- # starts a comment, rest of line is ignored
- whitespace separated (spaces in filenames must be escaped as "\ ")
- xxx   line oriented
- xxx  \ continues a [virtual] line.

Backup control files
--------------------
- include <path>
- exclude <shell-pattern>
- xxx? ignore-mode, ignore-ids, always-copy <shell-pattern>

File Lists
----------
- p1 <mode> <uid> <gid> <size> <atime> <mtime> <flags> <path>
  - <flags> may be ´´-´´ if not supported
  - directory or file etc is determined by <mode>
  - all fields except <path> are decimal numbers, access and modification times
    are floats the others integers.
  - <path> must not contain spaces. escapes are allowed, including ´´\ ´´


TODO and ideas
==============
- commands
  - list one file in all backups
  - grep contents of [one] file[s] in all backups
  - restore recursively, optionally redirect to new location
  - autoclean -> remove incomplete backups
  - compare -> compare stat values on one/all backups and original
  - purge remove complete backups
- differential time specs: lttp cat /some/file -t "1 month ago"
- change detection via hash sums or other means? there may be applications
  that change files, keeping the size and faking the mtime.
- do not cross filesystems, stat/st_dev
- automatically load config file from target location
- timespec module, regexp
- profile module
  - search ~/.lttp and ./lttp
- config file_
  - include PATH
  - force-copy PATTERN
- how to handle filenames with encoding errors?

- idea for exclude pattern: "nobackup" in filename
- rangliste der grössten files bei backup, frage befor start
- checksumme für verify? disk errors...
