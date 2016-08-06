#!/usr/bin/env python3
# encoding: utf-8
#
# (C) 2012-2016 Chris Liechti <cliechti@gmx.net>
#
# SPDX-License-Identifier:    BSD-3-Clause

from link_to_the_past import *

import sys
import os
import codecs
import re

m_comment = re.compile('(#.*$)', re.UNICODE)    # regexp to remove line comments


class Word(str):
    """\
    Like a string but annotated with the position in the source file it was read from.
    """
    def __new__(cls, word, filename, lineno, text):
        self = str.__new__(cls, word)
        self.filename = filename
        self.lineno = lineno
        self.text = text
        return self

    def __repr__(self):
        return "Word({}, {!r}, {!r})".format(
            str.__repr__(self),
            self.filename,
            self.lineno)


def words_in_file(filename, fileobj=None, include_newline=False):
    """\
    Yield word for word of a file, with comments removed. Words are annotated
    with position in source file.
    """
    if fileobj is None:
        fileobj = codecs.open(filename, 'r', 'utf-8')
    for n, line in enumerate(fileobj, 1):
        # - ensure escaped spaces are do not include a space "\ " -> "\x20"
        # - remove comment
        # - remove whitespace and beginning and end
        # - split on whitespace
        for word in m_comment.sub('', line.replace('\ ', '\\x20')).split():
            yield Word(word, filename, n, line)
        if include_newline:
            yield Word('\n', filename, n, line)


class ControlFileParser(object):
    """\
    Parser for a simple language using white space separated words (like
    Forth).

    Languages can be implemented by subclassing this one. Words are looked up
    on self, searching for methods with the name ``word_xxx`` where xxx stands
    for the word in lower case.
    """
    def __init__(self):
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
        return self._iterator.__next__()

    def interpret(self, word):
        a = 'word_{}'.format(word.lower())
        if hasattr(self, a):
            function = getattr(self, a)
            function()
        else:
            raise SyntaxError('unknown word: {!r}'.format(word))

    def path(self, path):
        """\
        Convert path to an absolute path. If it was relative, it is relative to
        the location of the loaded configuration file.
        """
        path = os.path.expandvars(os.path.expanduser(path))
        if not os.path.isabs(path):
            path = os.path.join(self.root, path)
        return path

    def load_file(self, filename):
        """\
        Load configuration file. Path of file is remembered so that contained
        paths can be relative to the file.
        """
        self.root = os.path.dirname(os.path.abspath(filename))
        self.parse(words_in_file(filename))

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

if __name__ == '__main__':
    b = Backup()
    p = BackupControl(b)
    p.parse(words_in_file(sys.argv[1]))
    print(b)
    print(b.source_locations)
    print(b.source_locations[-1].excludes)
