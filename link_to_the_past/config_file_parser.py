#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 Chris Liechti <cliechti@gmx.net>
# All Rights Reserved.
# Simplified BSD License (see LICENSE.txt for full text)

from link_to_the_past import *

import sys
import os
import codecs
import re
import logging

m_comment = re.compile('(#.*$)', re.UNICODE)    # regexp to remove line comments

class Word(unicode):
    """\
    Like a string but annotated with the position in the source file it was read from.
    """
    def __new__(cls, word, filename, lineno, text):
        self = unicode.__new__(cls, word)
        self.filename = filename
        self.lineno = lineno
        self.text = text
        return self

    def __repr__(self):
        return "Word(%s, %r, %r)" % (
                unicode.__repr__(self),
                self.filename,
                self.lineno)

def words_in_file(filename, fileobj=None, include_newline=False):
    """\
    Yield word for word of a file, with comments removed. Words are annotated
    with position in source file.
    """
    if fileobj is None:
        fileobj = codecs.open(filename, 'r', 'utf-8')
    for n, line in enumerate(fileobj):
        for word in m_comment.sub('', line).split():
            yield Word(word, filename, n+1, line)
        if include_newline:
            yield Word('\n', filename, n+1, line)


class ContolFileParser(object):

    def __init__(self, backup):
        self.backup = backup
        self.root = '.'

    def parse(self, iterator):
        self._iterator = iterator   # used in next_word
        try:
            while True:
                self.interpret(self.next_word())
        except StopIteration:
            pass
        self._iterator = None

    def next_word(self):
        return self._iterator.next()

    def interpret(self, word):
        a = 'word_%s' % (word,)
        if hasattr(self, a):
            function = getattr(self, a)
            function()
        else:
            raise SyntaxError('unknown word: %r' % (word,))

    def path(self, path):
        if not os.path.isabs(path):
            path = os.path.join(self.root, path)
        return path

    def load_file(self, filename):
        self.root = os.path.dirname(os.path.abspath(filename))
        self.parse(words_in_file(filename))


class BackupControl(ContolFileParser):

    def word_target(self):
        self.backup.set_target_path(self.path(self.next_word()))

    def word_location(self):
        self.backup.source_locations.append(Location(self.path(self.next_word())))

    #~ def word_include(self):
    def word_exclude(self):
        self.backup.source_locations[-1].excludes.append(ShellPattern(self.next_word()))


if __name__ == '__main__':
    b = Backup('example_backups')
    p = BackupControl(b)
    p.parse(words_in_file(sys.argv[1]))
    print b
    print b.source_locations
    print b.source_locations[-1].excludes


