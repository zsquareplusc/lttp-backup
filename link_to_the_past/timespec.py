#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""\
Link To The Past - a backup tool

Parse time specification for locating old backups.

(C) 2012 cliechti@gmx.net
"""

def get_by_timespec(backups, timespec):
    """\
    backups is a list of names of backups (strings representing dates)
    timespec is a string describing a date, time difference or order
    """
    if timespec is None or timespec == 'last':
        return backups[-1]
    elif timespec == 'previous':
        return backups[-2]
    elif timespec == 'first':
        return backups[0]
    # XXX add things like "1 week ago"
    else:
        # search for date
        # XXX this is just string in string
        for backup in backups:
            if timespec in backup:
                return backup
    raise KeyError('No backup found matching %r' % (timespec,))

