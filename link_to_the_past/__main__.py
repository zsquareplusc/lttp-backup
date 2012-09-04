#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""\
Link To The Past - a backup tool

Command line front-end.

(C) 2012 cliechti@gmx.net
"""

import sys

from link_to_the_past import create, restore

def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'create':
        del sys.argv[1]
        create.main()
    else:
        restore.main()


if __name__ == '__main__':
    main()
