#! /usr/bin/env python2

# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, see
# <http://www.gnu.org/licenses/>.


"""
Python Javatools

author: Christopher O'Brien  <obriencj@gmail.com>
license: LGPL v.3
"""


import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

from extras import pylint_cmd, cheetah_build_py_cmd


setup(name = "javatools",
      version = "1.4.0",

      packages = [ "javatools",
                   "javatools.cheetah" ],

      package_data = { "javatools.cheetah": [ "data/*.css",
                                              "data/*.js",
                                              "data/*.png" ] },

      scripts = [ "scripts/classdiff",
                  "scripts/classinfo",
                  "scripts/distdiff",
                  "scripts/distinfo",
                  "scripts/jardiff",
                  "scripts/jarinfo",
                  "scripts/jarutil",
                  "scripts/manifest" ],

      test_suite = "tests",

      # PyPI information
      author = "Christopher O'Brien",
      author_email = "obriencj@gmail.com",
      url = "https://github.com/obriencj/python-javatools",
      license = "GNU Lesser General Public License",

      description = "Tools for finding meaningful deltas in Java"
      " class files and JARs",

      provides = [ "javatools" ],
      requires = [ "Cheetah" ],
      platforms = [ "python2 >= 2.6" ],

      classifiers = [ "Development Status :: 5 - Production/Stable",
                      "Environment :: Console",
                      "Intended Audience :: Developers",
                      "Intended Audience :: Information Technology",
                      "Programming Language :: Python :: 2",
                      "Topic :: Software Development :: Disassemblers" ],

      # extras stuff
      cmdclass = { 'build_py': cheetah_build_py_cmd,
                   'pylint': pylint_cmd } )


#
# The end.
