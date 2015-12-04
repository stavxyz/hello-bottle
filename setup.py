#!/usr/bin/env python

from __future__ import print_function

import os
import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


here = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(here, 'hello.py'), 'r') as abt:
    marker, about, abt = '# __about__', {}, abt.read()
    assert abt.count(marker) == 2
    abt = abt[abt.index(marker):abt.rindex(marker)]
    other = {}
    exec(abt, {'__builtins__': {}}, about)


ENTRY_POINTS = {
    'console_scripts': [
        'hello-bottle=hello:cli'
    ]
}


INSTALL_REQUIRES = [
    'bottle>=0.12.9',
    'pymongo>=3.1.1',

]


CLASSIFIERS = [
    'Intended Audience :: Developers',
    'Operating System :: OS Independent',
    'Topic :: Software Development',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.6',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.2',
    'Programming Language :: Python :: 3.3',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: Implementation :: CPython',
    'Programming Language :: Python :: Implementation :: PyPy',
]


package_attributes = {
    'author': about['__author__'],
    'author_email': about['__email__'],
    'classifiers': CLASSIFIERS,
    'description': about['__summary__'],
    'entry_points': ENTRY_POINTS,
    'install_requires': INSTALL_REQUIRES,
    'keywords': ' '.join(about['__keywords__']),
    'name': about['__title__'],
    'py_modules': ['hello'],
    'url': about['__url__'],
    'version': about['__version__'],
}

setup(**package_attributes)
