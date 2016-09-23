#!/usr/bin/env python3
# encoding: utf-8
#
# (C) 2012-2016 Chris Liechti <cliechti@gmx.net>
#
# SPDX-License-Identifier:    BSD-3-Clause
"""\
Parser for a white space separated words, so that mini languages can be
implemented. It's a Forth like syntax.
"""
import os
import re

m_comment = re.compile('(#.*$)', re.UNICODE)    # regexp to remove line comments


class Word(str):
    """\
    Like a string but annotated with the position in the source file it was read
    from.

    >>> print(Word('hello', 'world.txt', 1))
    hello
    >>> Word('hello', 'world.txt', 1)
    Word('hello', 'world.txt', 1)
    """
    __slots__ = ['filename', 'lineno']

    def __new__(cls, word, filename, lineno):
        self = str.__new__(cls, word)
        self.filename = filename
        self.lineno = lineno
        return self

    def lower(self):
        return Word(str.lower(self), self.filename, self.lineno)

    def __repr__(self):
        """\
        >>> print(repr(Word('hello', 'world.txt', 1)))
        Word('hello', 'world.txt', 1)
        """
        return "Word({}, {!r}, {!r})".format(
            str.__repr__(self),
            self.filename,
            self.lineno)


def words_in_file(filename, fileobj=None, include_newline=False):
    """\
    Yield word for word of a file, with comments removed. Words are annotated
    with position in source file.

    >>> z = words_in_file('dummy', ['first line', 'second line'])
    >>> list(z)
    [Word('first', 'dummy', 1), Word('line', 'dummy', 1), Word('second', 'dummy', 2), Word('line', 'dummy', 2)]
    """
    if fileobj is None:
        fileobj = open(filename, 'r', encoding='utf-8')
    for n, line in enumerate(fileobj, 1):
        # - ensure escaped spaces do not include a space "\ " -> "\x20"
        # - remove comment
        # - remove whitespace and beginning and end
        # - split on whitespace
        for word in m_comment.sub('', line.replace('\ ', '\\x20')).split():
            yield Word(word, filename, n)
        if include_newline:
            yield Word('\n', filename, n)


def words_in_file_quick(filename, fileobj=None):
    """\
    Yield word for word of a file, with comments removed.

    >>> z = words_in_file_quick('dummy', ['first line', 'second line'])
    >>> list(z)
    ['first', 'line', 'second', 'line']
    """
    if fileobj is None:
        fileobj = open(filename, 'r', encoding='utf-8')
    for line in fileobj:
        # - ensure escaped spaces do not include a space "\ " -> "\x20"
        # - remove comment
        # - remove whitespace and beginning and end
        # - split on whitespace
        for word in m_comment.sub('', line.replace('\ ', '\\x20')).split():
            yield word


class ControlFileParser(object):
    """\
    Parser for a simple language using white space separated words (like
    Forth).

    Languages can be implemented by subclassing this one. Words are looked up
    on self, searching for methods with the name ``word_xxx`` where xxx stands
    for the word in lower case.

    >>> class Lang(ControlFileParser):
    ...     def word_hello(self):
    ...         print("hello")
    >>> lang = Lang()
    >>> lang.parse(iter(['hello', 'hello']))
    hello
    hello
    """
    def __init__(self):
        self.root = '.'

    def parse(self, iterator):
        """Execute each word in a sequence"""
        self._iterator = iterator   # used in next_word
        for word in iterator:
            self.interpret(word)
        self._iterator = None

    def next_word(self):
        """\
        Get the next word from a sequence, can be used by words to get
        parameters.
        >>> class Lang(ControlFileParser):
        ...     def word_print(self):
        ...         print(self.next_word())
        >>> lang = Lang()
        >>> lang.parse(iter(['print', 'hello', 'print', 'world']))
        hello
        world
        """
        return self._iterator.__next__()

    def interpret(self, word):
        """\
        Interpret a single word.

        >>> class Lang(ControlFileParser):
        ...     def word_hello(self):
        ...         print("hello")
        >>> lang = Lang()
        >>> lang.interpret('hello')
        hello
        >>> lang.interpret('world')
        Traceback (most recent call last):
        ...
        SyntaxError: unknown word: 'world'
        """
        try:
            function = getattr(self, 'word_{}'.format(word.lower()))
        except AttributeError:
            raise SyntaxError('unknown word: {!r}'.format(word))
        else:
            function()

    def path(self, path):
        """\
        Convert path to an absolute path. If it was relative, it is relative to
        the location of the loaded configuration file.

        >>> c = ControlFileParser()
        >>> c.path('somewhere')
        './somewhere'
        >>> c.root = '/at/some/point'
        >>> c.path('somewhere')
        '/at/some/point/somewhere'
        >>> c.path('/already/there')
        '/already/there'
        """
        path = os.path.expandvars(os.path.expanduser(path))
        if not os.path.isabs(path):
            path = os.path.join(self.root, path)
        return path

    def load_file(self, filename, quick=False):
        """\
        Load configuration file. Path of file is remembered so that contained
        paths can be relative to the file.
        """
        self.root = os.path.dirname(os.path.abspath(filename))
        if quick:
            self.parse(words_in_file_quick(filename))
        else:
            self.parse(words_in_file(filename))


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
if __name__ == '__main__':
    import doctest
    doctest.testmod()
