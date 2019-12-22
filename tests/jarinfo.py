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
unit tests for javatools/jarinfo.py

author: Konstantin Shemyak  <konstantin@shemyak.com>
license: LGPL v.3
"""

import os
from unittest import TestCase
from . import get_data_fn
from javatools.jarinfo import main


class JarinfoTest(TestCase):

    jar = get_data_fn(os.path.join("test_jarinfo", "Sample.jar"))

    # classinfo-specific option is accepted:
    def test_classinfo_options(self):
        self.assertEqual(0, main(["argv0", "-p", self.jar]))

    # Test that a classinfo-specific option is accepted.
    def test_jarinfo_options(self):
        self.assertEqual(0, main(["argv0", "--jar-classes", self.jar]))

    def test_jarinfo_manifest(self):
        """ Manifest CLI option is accepted """
        self.assertEqual(0, main(["argv0", "--manifest", self.jar]))
