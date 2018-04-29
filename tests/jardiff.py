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

import os
from unittest import TestCase
from . import get_data_fn
from javatools.jardiff import cli_jars_diff, main


class OptionsHolder(object):
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
        self.cli_jardiff_wrap(0, "test_jardiff/ec.jar", "test_jardiff/ec-copied.jar",
            "Identical JARs reported as different")

    def test_sig_block_file_tampered(self):
        self.cli_jardiff_wrap(1, "test_jardiff/ec.jar", "test_jardiff/ec-tampered.jar",
            "Change in signature block file is not detected")

    def test_sig_block_file_removed(self):
        self.cli_jardiff_wrap(1, "test_jardiff/ec.jar", "test_jardiff/ec-sig-block-removed.jar",
            "Removal of signature block file is not detected")

    def test_sig_manifest_tampered(self):
        self.cli_jardiff_wrap(1, "test_jardiff/ec.jar", "test_jardiff/ec-sig-mf-tampered.jar",
            "Change in manifest signature file is not detected")

    def test_generic_file_change(self):
        self.options.ignore_jar_entry = []  # Needed, as argparse is not called
        self.cli_jardiff_wrap(1, os.path.join("test_jardiff", "generic1.jar"),
            os.path.join("test_jardiff", "generic2.jar"),
            "Change in generic file is not detected")

    def test_json_binary_diff(self):
        left = get_data_fn(os.path.join("test_jardiff", "ec.jar"))
        right = get_data_fn(os.path.join("test_jardiff", "ec-tampered.jar"))
        self.assertEqual(1, main(["argv0", "--json", left, right]))

    # Options from relevant option groups are accepted:
    def test_options_accepted(self):
        left = get_data_fn(os.path.join("test_jardiff", "ec.jar"))
        right = get_data_fn(os.path.join("test_jardiff", "ec-tampered.jar"))
        # General options:
        self.assertEqual(1, main(["argv0", "-q", left, right]))
        # JAR checking options:
        self.assertEqual(0, main(["argv0", "--ignore-jar-signature", left, right]))
        # Class checking options:
        self.assertEqual(1, main(["argv0", "--ignore-platform-up", left, right]))
        # Reporting options:
        self.assertEqual(1, main(["argv0", "--report-dir=foo", left, right]))
        # JSON reporting options:
        self.assertEqual(1, main(["argv0", "--json", "--json-indent=4", left, right]))
        # HTML reporting options:
        self.assertEqual(1, main(["argv0", "--html-copy-data=foo", left, right]))


#
# The end.
