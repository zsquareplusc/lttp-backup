#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""\
Link To The Past - a backup tool

Command line front-end.

(C) 2012 cliechti@gmx.net
"""

import sys

from link_to_the_past import create, restore, edit, compare

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == 'create':
            del sys.argv[1]
            return create.main()
        elif sys.argv[1] == 'rm':
            return edit.main()
        elif sys.argv[1] == 'verify':
            return compare.main()
    return restore.main()


if __name__ == '__main__':
    main()
