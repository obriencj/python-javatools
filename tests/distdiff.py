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
unit tests for javatools/classinfo.py

author: Konstantin Shemyak  <konstantin@shemyak.com>
license: LGPL v.3
"""

import os
from unittest import TestCase
from . import get_data_fn
from javatools.distdiff import main


class DistdiffTest(TestCase):

    # Options from relevant option groups are accepted:
    def test_options_accepted(self):
        left = get_data_fn(os.path.join("test_distdiff", "dist1"))
        right = get_data_fn(os.path.join("test_distdiff", "dist2"))
        # General options:
        self.assertEqual(1, main(["argv0", "-q", left, right]))
        # Distdiff options:
        self.assertEqual(1, main(["argv0", "--processes=1", left, right]))
        # JAR checking options:
        self.assertEqual(1, main(["argv0", "--ignore-jar-signature", left, right]))
        # Class checking options:
        self.assertEqual(1, main(["argv0", "--ignore-platform-up", left, right]))
        # Reporting options:
        self.assertEqual(1, main(["argv0", "--report-dir=foo", left, right]))
        # JSON reporting options:
        self.assertEqual(1, main(["argv0", "--json-indent=4", left, right]))
        # HTML reporting options:
        self.assertEqual(1, main(["argv0", "--html-copy-data=foo", left, right]))

    def test_changed_text(self):
        left = get_data_fn(os.path.join("test_distdiff", "text1"))
        right = get_data_fn(os.path.join("test_distdiff", "text2"))
        self.assertEqual(1, main(["argv0", left, right]))

    def test_different_manifests(self):
        left = get_data_fn(os.path.join("test_distdiff", "mf1"))
        right = get_data_fn(os.path.join("test_distdiff", "mf2"))
        self.assertEqual(1, main(["argv0", left, right]))
