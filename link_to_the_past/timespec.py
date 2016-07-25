#!/usr/bin/env python3
# encoding: utf-8
#
# (C) 2012-2016 Chris Liechti <cliechti@gmx.net>
#
# SPDX-License-Identifier:    BSD-3-Clause
"""\
Link To The Past - a backup tool

Parse time specification for locating old backups.
"""
import datetime

from .error import BackupException


def get_limit(timespec, now=None):
    """\
    Parse a string describing a time difference from now.
    It returns a time right after the desired point. The idea is to use it this
    way:
        if some_time < limit:
            print "It is older"

    The ``now`` parameter is there only for testing purposes.

    >>> today = datetime.datetime(2012, 4, 1, 16, 55)
    >>> get_limit('1 hour ago', today)
    datetime.datetime(2012, 4, 1, 15, 55)
    >>> get_limit('yesterday', today)
    datetime.datetime(2012, 4, 1, 0, 0)
    >>> get_limit('1 day ago', today)
    datetime.datetime(2012, 4, 1, 0, 0)
    >>> get_limit('2 days ago', today)
    datetime.datetime(2012, 3, 31, 0, 0)
    >>> get_limit('2 weeks ago', today)
    datetime.datetime(2012, 3, 19, 0, 0)
    >>> get_limit('1 month ago', today)     # XXX not yet accurate
    datetime.datetime(2012, 3, 2, 0, 0)
    >>> get_limit('1 year ago', today)      # XXX not yet accurate
    datetime.datetime(2011, 4, 3, 0, 0)
    """
    if now is None:
        now = datetime.datetime.now()
    if timespec.endswith('ago'):
        amount, unit, ago = timespec.split()
        if unit in ('hour', 'hours'):
            delta = datetime.timedelta(seconds=3600*int(amount))
            return now - delta
        elif unit in ('day', 'days'):
            delta = datetime.timedelta(days=int(amount)-1)
        elif unit in ('week', 'weeks'):
            delta = datetime.timedelta(days=7*int(amount)-1)
        elif unit in ('month', 'months'):
            delta = datetime.timedelta(days=31*int(amount)-1)  # XXX not exact months
        elif unit in ('year', 'years'):
            delta = datetime.timedelta(days=365*int(amount)-1)  # XXX not exact years
        else:
            raise ValueError('do not recognize unit (2nd word) in: {!r}'.format(timespec))
        limit = datetime.datetime(now.year, now.month, now.day) - delta
    elif timespec == 'yesterday':
        limit = datetime.datetime(now.year, now.month, now.day)
    else:
        raise ValueError('do not recognize time specification: {!r}'.format(timespec))
    return limit


def get_by_timespec(backups, timespec):
    """\
    backups is a list of names of backups (strings representing dates)
    timespec is a string describing a date, time difference or order
    """
    backups.sort()
    # by order
    if timespec is None or timespec == 'last':
        return backups[-1]
    elif timespec == 'previous':
        return backups[-2]
    elif timespec == 'first':
        return backups[0]
    elif timespec.startswith('-'):
        n = int(timespec)
        if -len(backups) < n < 0:
            return backups[n]
    else:
        # by absolute date, just compare strings
        latest_match = None
        for backup in backups:
            if backup.startswith(timespec):
                latest_match = backup
        if latest_match is not None:
            return latest_match
        # by time delta description
        limit = get_limit(timespec)
        for backup in backups:
            t = datetime.datetime.strptime(backup, '%Y-%m-%d_%H%M%S')
            if t < limit:
                latest_match = backup
        if latest_match is not None:
            return latest_match
    raise BackupException('No backup found matching {!r}'.format(timespec))

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

if __name__ == '__main__':
    import doctest
    doctest.testmod()
