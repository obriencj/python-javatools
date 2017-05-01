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
unit tests for javatools/distinfo.py

author: Konstantin Shemyak  <konstantin@shemyak.com>
license: LGPL v.3
"""

import os
from unittest import TestCase
from . import get_data_fn
from javatools.distinfo import main


class DistinfoTest(TestCase):

    dist = get_data_fn(os.path.join("test_distinfo", "dist1"))

    # classinfo-specific option is accepted:
    def test_classinfo_options(self):
        self.assertEqual(0, main(["argv0", "-p", self.dist]))

    # jarinfo-specific option is accepted:
    def test_jarinfo_options(self):
        self.assertEqual(0, main(["argv0", "--jar-classes", self.dist]))

    # distinfo-specific option is accepted:
    def test_distinfo_options(self):
        self.assertEqual(0, main(["argv0", "--dist-provides", self.dist]))
