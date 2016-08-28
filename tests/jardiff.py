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
unit tests for creating/modifying JAR files with python-javatools.

author: Konstantin Shemyak  <konstantin@shemyak.com>
license: LGPL v.3
"""

from unittest import TestCase
from . import get_data_fn
from javatools.jardiff import cli_jars_diff


class OptionsHolder:
    pass

class JardiffTest(TestCase):

    options = OptionsHolder()

    def cli_jardiff_wrap(self, expected, left, right, message):
            self.assertEqual(expected, cli_jars_diff(self.options,
                get_data_fn(left),
                get_data_fn(right)),
                message)

    options.silent = True
    options.ignore_jar_signature = False

    # Two identical JARs (in different files, just in case)
    def test_identical_jars(self):
        self.cli_jardiff_wrap(0, "ec.jar", "ec-copied.jar",
            "Identical JARs reported as different")

    def test_sig_block_file_tampered(self):
        self.cli_jardiff_wrap(1, "ec.jar", "ec-tampered.jar",
            "Change in signature block file is not detected")

    def test_sig_block_file_removed(self):
        self.cli_jardiff_wrap(1, "ec.jar", "ec-tampered.jar",
            "Removal of signature block file is not detected")

    def test_sig_manifest_tampered(self):
        self.cli_jardiff_wrap(1, "ec.jar", "ec-sig-mf-tampered.jar",
            "Change in manifest signature file is not detected")


#
# The end.