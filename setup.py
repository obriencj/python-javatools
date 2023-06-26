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


from setuptools import setup as _setup


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


def setup():
    return _setup(cmdclass={'build_py': delayed_cheetah_build_py_cmd, })


if __name__ == '__main__':
    setup()


#
# The end.
