#! /usr/bin/env python

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


from setuptools import setup


PYTHON_SUPPORTED_VERSIONS = (
    ">=2.7",
    "!=3.0.*", "!=3.1.*", "!=3.2.*", "!=3.3.*", "!=3.4.*",
    "<4",
)


def delayed_cheetah_build_py_cmd(*args, **kwds):
    # only import cheetah_build_py_cmd immediately before
    # instantiating it.
    from javatools.cheetah.setuptools import cheetah_build_py_cmd
    return cheetah_build_py_cmd(*args, **kwds)


setup(name = "javatools",
      version = "1.5.0",

      packages = [
          "javatools",
          "javatools.cheetah",
      ],

      package_data = {
          "javatools.cheetah": [
              "*.tmpl",
              "data/*.css",
              "data/*.js",
              "data/*.png",
          ],
      },

      entry_points = {
          "console_scripts": [
              'classdiff=javatools.classdiff:main',
              'classinfo=javatools.classinfo:main',
              'distdiff=javatools.distdiff:main',
              'distinfo=javatools.distinfo:main',
              'jardiff=javatools.jardiff:main',
              'jarinfo=javatools.jarinfo:main',
              'jarutil=javatools.jarutil:main',
              'manifest=javatools.manifest:main',
          ],
      },

      test_suite = "tests",

      # PyPI information
      author = "Christopher O'Brien",
      author_email = "obriencj@gmail.com",
      url = "https://github.com/obriencj/python-javatools",
      license = "GNU Lesser General Public License v.3",

      description = "Tools for finding meaningful deltas in Java"
      " class files and JARs",

      provides = [
          "javatools",
      ],

      install_requires = [
          "Cheetah3",
          "M2Crypto >= 0.26.0",
          "six",
      ],

      setup_requires = [
          "Cheetah3",
          "six",
      ],

      python_requires = ", ".join(PYTHON_SUPPORTED_VERSIONS),

      classifiers = [
          "Development Status :: 5 - Production/Stable",
          "Environment :: Console",
          "Intended Audience :: Developers",
          "Intended Audience :: Information Technology",
          "Programming Language :: Python :: 2.7",
          "Programming Language :: Python :: 3.5",
          "Programming Language :: Python :: 3.6",
          # "Programming Language :: Python :: 3.7",
          "Topic :: Software Development :: Disassemblers",
      ],

      # extras stuff
      cmdclass = {'build_py': delayed_cheetah_build_py_cmd, })


#
# The end.
