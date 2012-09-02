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


The backup is always a simply copy of the files. This ensures that the backup
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
- XXX Symbolic links can not be checked for modifications and are therefore always
  copied.
- Time stamps are stored in microsecond resolution (some file systems allow
  higher accuracy, if this is need by the application, do not use this backup
  tool). Change detection works at a resolution of 10µs (this should not be a
  problem as making a backup certainly takes longer than that).


Configuration file format
=========================
- line oriented
- # starts a comment, rest of line is ignored
- \ continues a [virtual] line.
- whitespace separated (spaces in filenames must be escaped as \x20)

Backup control files
--------------------
- include <path>
- exclude <shell-pattern>
- xxx? ignore-mode, ignore-ids, always-copy <shell-pattern>

File Lists
----------
- dir <mode> <uid> <gid> <path>
- f <mode> <uid> <gid> <size> <path>
- l <path>


TODO and ideas
==============
- save file list, load that list for last backup instead of scanning
- make items read-only, store permissions elsewhere
- command line tool
- list, backup, restore, cat, grep commands
  - list backups
  - list files in one backup
  - list one file in all backups
  - grep contents of [one] file[s] in all backups
  - cat, output one file in one backup
  - cp, copy a file from one backup to given target path or file name
- differential time specs: lttp cat /some/file -t "1 month ago"
- track changes in contents and meta data separately. there is no need to copy
  the file if just some meta data has changed (e.g. uid, permissions)
- change detection via hash sums or other means? there may be applications
  that change files, keeping the size and faking the mtime.
- do not cross filesystems
- option to leave out hard links -> just incremental copies. for dumb
  filesystems as target. better than no backup..

notes
D 0666 1000 1000 2137489234 /path/to/file
F 0666 1000 1000 230897423 1234 /path/to/directory
drwxrwxr-x 1000 1000 812 230897423 /path/to/directory
# comment, line continuation \

include /home/lch
exclude */.gvfs
