=========================
 Link To The Past Backup
=========================

Simple backup program.

The backup is always a simple copy of the files. This ensures that the backup
can be used in any point in the future. Even if the backup program is lost or
incompatible.

Key Features
------------

- Works incrementally while providing full backups at any time. Uses hard
  links to reference files from the previous backup, so each backup looks like
  a full backup, while saving space on all the files that have not changed.

- Changed files are copied entirely.

- Check before doing. Available space and capability to create the required
  number of files (inodes) is checked before the copying starts.

- Does not rely on external tools (``cp``, ``rsync`` etc.).


More Features
-------------

- Checksums may be calculated on backed up files. This allows to verify the
  backup (bad disk, modifications). It can also be used to check the
  original files against a previous backup.

- Files are checked by modification date and size.

- Does not erase failed backup. It's your decision to delete these. They
  can easilily be identified by the name of the directory (directories
  ending with ``..._incomplete``).

- File systems are not crossed. Use ``include`` directive in configuration
  file to manually include the path or an ``exclude`` directive to suppress
  the warning.


Caveats
-------

- Special files (devices) are not backed up. This means this backup solution
  is not suitable to secure the entire system. It's meant for user data.

- Files are checked by modification date and size. This is very fast to
  determine if a file has been changed. However, there are programs that
  reset the modification time even after modifications. Such files will
  not be detected!

- The target location needs to be in the file system. This tool does not
  support backing up via protocols like ssh, ftp etc. Typically the target
  will be a USB disk or memory stick but it also works well with storage in
  the network, e.g. a NAS mounted via NFS.

- Hard linked files only exist once on the disk. This is also a risk that when
  it is damaged (disk errors, manipulations), then the references in all
  backups are also damaged. To safeguard against this risk, it is advised to
  create full copies from time to time and/or use different disks to backup.

- Backups are timestamped, you can not create more than one backup per second
  :-)

- Time stamps are stored in microsecond resolution (some file systems allow
  higher accuracy, if this is need by the application, do not use this backup
  tool). Change detection works at a resolution of 10µs.

- Currently does not restore permissions on soft-links. This is not so
  critical as under normal use the permissions of a link are not used
  anyway (only the permissions of the target).

.. warning:: Filenames with encoding errors are skipped! (A warning is printed)


Yes it is not the first program of that kind. The reason it exists is that
existing programs did, for me, not work well with some files or amount of
data. There is no need to use ``rsync`` to make local copies. Analyzing the files
often takes more time than simply copying it.

File access is minimized as much as possible. Files in the backup are usually
accessed one time (copy or link then set permissions, make read-only).
Directories are accessed twice (create and in the end, make read-only).
Checksums are calculated on the fly as files are copied, data is read/written
exactly once.


Command Line Tool
=================

General options:
    -v                  make outputs more verbose, can be given multiple times
    -q                  switch off messages
    --debug             for the programmer: shows tracebacks for failures
    -c CONFIGURATION    load given configuration file
    -p PROFILENAME      load given profile. profiles are configuration files
                        in ``~/.link_to_the_past``.

Create Backups
--------------
``python -m link_to_the_past.create -c CONFIGURATION``

options:
    --full              copy all items, do not depend on last backup.
    -f, --force         create backup anyway, even if no files have changed


Restore Files
-------------
``python -m link_to_the_past.restore -c CONFIGURATION ACTION [...]``

Options:
    -t TIMESPEC         specify a backup, default (option not given, is to use
                        the latest backup)

Actions:
    list                list all backups
    ls [PATTERN]        list files of backup, optionally filtered by PATTERN
    cp SRC DST          copy a single file from the backup (SRC) to DST
    cp -r SRC DST       copy a directory recursively from the backup (SRC) to DST
    cat SRC             dump single file from the backup (SRC) to stdout
    path                print the absolute path to the backup


Compare Backups
---------------
These actions are used to compare two backups or a backup to the current
files.


``python -m link_to_the_past.compare -c CONFIGURATION ACTION [...]``

Options:
    -t TIMESPEC         specify a backup, default (option not given, is to use
                        the latest backup)

Actions:
    verify              compare files in the source location against the
                        backup (also compare hashes)
    integrity           check all files within the backup for changes (compare
                        hashes)
    changes TIMESPEC    compare two backups and list differences
                        added/changed/removed


Change Backups
--------------
These operations alter previously made backups. To be used with care!
There are actions to remove files and/or directories from backups or
remove entire backups.


``python -m link_to_the_past.edit -c CONFIGURATION ACTION [...]``

Options:
    -t TIMESPEC         specify a backup, default (option not given, is to use
                        the latest backup)

Actions:
    rm SRC              remove a file from the backup
    rm -r SRC           remove a directory and all its contents
    purge               removes the complete backup


Copy
----
The ``cp`` action copies files or directories from the backup to the given
destination. This is a convenient way to restore files in to a new location.

If the destination is a directory, the name of the source is used as name for the
file or directory that is being restored within given destination.

``cp`` restores the original permissions of the file.

.. warning:: Existing a file or directory with the same name will be overwritten!


Remove
------
The ``rm`` action deletes files from the backup. Its purpose is to remove
items that have been accidentally backed up (e.g. temporary files, caches,
sensitive content etc.).

.. warning:: This destroys the files in the backup, use with extreme care!

.. note:: It usually makes sense to add an ``exclude`` rule to the
          control file so that it is not included again in the next backup.

Purge
-----
This command completely deletes a backup. The backup that is affected is
selected with the ``-t`` option. There will be no way to get the files back!

.. warning:: This destroys the complete backup, use with extreme care!


timespec - time specifications
------------------------------
The ``-t`` option accepts the following expressions:

- ``last`` the most recent backup, same as omitting ``-t``
- ``previous`` one second most recent backup
- ``first`` the first and oldest one
- expressions ending in ``ago``, e.g.: ``1 hour ago``, ``1 day ago``
  supported units are ``hour``, ``day``, ``week``, ``month``, ``year`` as well
  as each of them in plural form with a ``s`` appended. The amount must be a
  positive integer number (> 0).
- ``yesterday`` is the same as ``1 day ago``
- dates such as ``2012-04-01``
- dates and times such as ``2012-04-01_1655``
- partial dates also work, ``2012`` or ``2012-04`` because the time
  specification is simply matched against the name of the backup on the disk
  and this name is simply the date/time strings as seen above. In case of
  multiple matches the most recent one is picked.

The ``changes`` action requires a ``TIMESPEC2`` argument which can also have
the value ``now`` to represent the current files instead of a backup.


Profiles
========
A profile is the same as a configuration file but located in a special place.
The idea is to make it easier to work with multiple configurations.

Without any ``-p`` or ``-c`` options, a default configuration is loaded.

Named profiles are loaded with the ``-p <name>`` option. A file 
``<name>.profile`` is searched in the users ``~/.config/link-to-the-past``
directory.


Configuration file format
=========================
- ``#`` starts a comment, the rest of line is ignored
- whitespace separated (spaces in filenames must be escaped as "\ ")
- the order of the commands is irrelevant
- xxx   line oriented
- xxx  \ continues a [virtual] line.

Backup control files
--------------------
``include <path>``
    adds the path to the backup

``exclude <shell-pattern>``
    excludes files and directories matching the pattern

``load_config <path>``
    Load an other configuration file. This may be useful if a common
    include/exclude list is (re-)used in different configuration files.

``hash <name>``
    Specify the hash function to use. No hashing will be performed if the
    directive is absent.

    Available hash functions:
    - CRC32 (non-cryptographic)
    - SHA-256
    - SHA-512
    - MD5 (collisions known)

    Note that the cryptographic value is very limited as long as the file list
    is stored alongside the backup. To secure against intentional changes, the
    file list has to be stored at a different, safe location or has to be
    protected by other means (e.g. PGP/gpg).

    CRC32 yields the shortest hash string which means the file list stays
    smaller compared to the other algorithms, it is not cryptographic though.

- xxx? ignore-mode, ignore-ids, always-copy <shell-pattern>


File Lists
----------
``hash <name>``
    Specify the hash function to use.
    See also ``hash`` directive of the control file format above.

``p1 <mode> <uid> <gid> <size> <atime> <mtime> <flags> <hash> <path>``
    - ``<flags>`` may be ``-`` if not supported
    - directory or file etc. is determined by ``<mode>``
    - all fields except ``<hash>`` and ``<path>`` are decimal numbers, access and
      modification times are floats the others integers.
    - ``<path>`` must not contain spaces. escapes are allowed, including ``"\ "``.
    - ``<hash>`` is a string of printable characters, e.g. ``123ABC4D``.
      See also ``hash`` directive above.


TODO and ideas
==============
- commands
  - list one file in all backups
  - grep contents of [one] file[s] in all backups
  - locate -> search for matching filenames
  - autoclean -> remove incomplete backups
- change detection via hash sums or other means? there may be applications
  that change files, keeping the size and faking the mtime.
- config file
  - force-copy PATTERN
  - enable-checksum PATTERN

- idea for exclude pattern: "nobackup" in filename
- rangliste der grössten files bei backup, frage bevor start
- expand list command:
  include date like, "this week", "monday, two weeks ago", "yesterday",
  "today", "last month", "last year" etc.


Indexer
- excludes
- includes

CreateBackup
- source_root
- backup_root

RestoreBackup
- backup_root

CompareBackup
- root1
- root2
