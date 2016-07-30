# setup.py for Link To The Past Backup
#
# (C) 2016 Chris Liechti <cliechti@gmx.net>
#
# SPDX-License-Identifier:    BSD-3-Clause
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name="lttp-backup",
    description="Link To The Past Backup",
    version='0.1',
    author="Chris Liechti",
    author_email="cliechti@gmx.net",
    url="https://github.com/zsquareplusc/lttp-backup",
    packages=['link_to_the_past'],
    scripts=['lttp'],
    license="BSD",
    long_description=open('README.rst').read(),
    classifiers=[
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Intended Audience :: End Users/Desktop',
        'Environment :: Console',
        'Topic :: System :: Archiving :: Backup',
        'Operating System :: POSIX',
    ],
)
