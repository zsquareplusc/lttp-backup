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

from link_to_the_past import create, restore, edit, compare, profile
from link_to_the_past.error import BackupException

class HelpAllAction(argparse.Action):

    def __init__(self,
                 option_strings,
                 dest,
                 default=False,
                 required=False,
                 help=None):
        super().__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=0,
            help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        parser.print_help()

        # retrieve subparsers from parser
        subparsers_actions = [
            action for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)]
        # there will probably only be one subparser_action,
        # but better save than sorry
        for subparsers_action in subparsers_actions:
            # get all subparsers and print help
            for choice, subparser in subparsers_action.choices.items():
                print('==== action "{}" ===='.format(choice))
                print(subparser.format_help())
        parser.exit()


def main():
    parser = argparse.ArgumentParser()

    group = parser.add_argument_group('Messages')
    group.add_argument(
        "--develop",
        help="show technical details",
        default=False,
        action='store_true')
    group = group.add_mutually_exclusive_group()
    group.add_argument(
        "-v", "--verbose",
        dest="verbosity",
        help="increase level of messages (can be applied multiple times)",
        default=1,
        action='count')
    group.add_argument(
        "-q", "--quiet",
        dest="verbosity",
        help="disable messages (opposite of --verbose)",
        const=0,
        action='store_const')

    group = parser.add_argument_group('Backup Configuration')
    group = group.add_mutually_exclusive_group()
    group.add_argument(
        "-c", "--control",
        help="load control file at given path",
        metavar='FILE',
        default=None)
    group.add_argument(
        "-p", "--profile",
        help="load named profile (located in default config directory)",
        metavar='NAME',
        default=None)

    parser.add_argument(
        "--help-all",
        help="show help for all actions",
        action=HelpAllAction)

    subparsers = parser.add_subparsers(metavar='ACTION')
    # get the subcommands from the other modules
    for module in (create, edit, compare, restore):
        module.update_argparse(subparsers)
    args = parser.parse_args()

    if args.verbosity > 1:
        level = logging.DEBUG
    elif args.verbosity:
        level = logging.INFO
    else:
        level = logging.ERROR
    logging.basicConfig(
        level=level,
        format='%(levelname)s%(message)s\x1b[0m')
    logging.addLevelName(logging.DEBUG, '\x1b[2m⋅ ')
    logging.addLevelName(logging.INFO, '\x1b[2m• ')
    logging.addLevelName(logging.WARNING, '\x1b[33;1mWARNING: ')
    logging.addLevelName(logging.ERROR, '\x1b[31;1mERROR: ')

    if args.develop:
        logging.info('Command line arguments are {}'.format(args))

    logging.debug('Profile directory is "{}"'.format(profile.profile_directory))

    t_start = time.time()
    try:
        # execute the function that the subparser must set
        if hasattr(args, 'func'):
            args.func(args)
        else:
            parser.error('action misssing')
    except KeyboardInterrupt:
        logging.info('Aborted on user request.')
        sys.exit(1)
    except BackupException as e:
        if args.develop:
            raise
        logging.error('{}'.format(e))
        sys.exit(1)
    finally:
        t_end = time.time()
        logging.info('Action took {:.1f} seconds'.format(t_end - t_start))

if __name__ == '__main__':
    main()
