#!/usr/bin/env python3
# encoding: utf-8
#
# (C) 2012-2016 Chris Liechti <cliechti@gmx.net>
#
# SPDX-License-Identifier:    BSD-3-Clause
"""\
Link To The Past - a backup tool

Command line front-end.
"""

import argparse
import logging
import sys
import time

from link_to_the_past import create, restore, edit, compare
from link_to_the_past.error import BackupException


def main():
    parser = argparse.ArgumentParser()

    group = parser.add_argument_group('Messages')
    group.add_argument("--develop",
        help="show technical details",
        default=False,
        action='store_true'
    )
    group.add_argument("-v", "--verbose",
        dest="verbosity",
        help="increase level of messages",
        default=1,
        action='count'
    )
    group.add_argument("-q", "--quiet",
        dest="verbosity",
        help="disable messages (opposite of --verbose)",
        const=0,
        action='store_const'
    )

    group = parser.add_argument_group('Backup Configuration')
    group = group.add_mutually_exclusive_group()
    group.add_argument("-c", "--control",
        help="load control file",
        metavar='FILE',
        default=None,
    )
    group.add_argument("-p", "--profile",
        help="load named profile",
        metavar='NAME',
        default=None,
    )

    subparsers = parser.add_subparsers()
    # get the subcommands from the other modules
    for module in (create, edit, compare, restore):
        module.update_argparse(subparsers)
    # execute the function that the subparser must set
    args = parser.parse_args()

    if args.verbosity > 1:
        level = logging.DEBUG
    elif args.verbosity:
        level = logging.INFO
    else:
        level = logging.ERROR
    logging.basicConfig(level=level)

    if args.develop:
        logging.info('Command line arguments are {}'.format(args))

    t_start = time.time()
    try:
        if hasattr(args, 'func'):
            args.func(args)
        else:
            parser.error('action misssing')
    except KeyboardInterrupt:
        sys.stderr.write('\nAborted on user request.\n')
        sys.exit(1)
    except BackupException as e:
        if args.develop: raise
        sys.stderr.write('ERROR: {}\n'.format(e))
        sys.exit(1)
    finally:
        t_end = time.time()
        logging.info('Action took {:.1f} seconds'.format(t_end - t_start))

if __name__ == '__main__':
    main()
