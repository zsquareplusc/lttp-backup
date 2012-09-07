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
        elif sys.argv[1] in edit.IMPLEMENTED_ACTIONS:
            return edit.main()
        elif sys.argv[1] in compare.IMPLEMENTED_ACTIONS:
            return compare.main()
        elif sys.argv[1] in restore.IMPLEMENTED_ACTIONS:
            return restore.main()
    sys.stderr.write('Usage: %s [options] ACTION [...]\n\n' % (sys.argv[0],))
    sys.stderr.write('%s: error: missing ACTION\n' % (sys.argv[0],))
    sys.exit(1)


if __name__ == '__main__':
    main()
