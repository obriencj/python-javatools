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
unit tests for manifest-related functionality of python-javatools

author: Christopher O'Brien  <obriencj@gmail.com>
license: LGPL v.3
"""

from unittest import TestCase
from javatools.manifest import Manifest
import subprocess
import StringIO


class ManifestTest(TestCase):
    
    src_dir = "tests/data/"

    ##### Auxiliary functions for tests

    def manifest_cli_create(self, args, expected_result):

        source = self.src_dir + "test-manifest.jar"

        with open(self.src_dir + expected_result) as f:
            expected_result = f.read()

        result = subprocess.check_output([ "manifest", "-c" ] + args.split() + [ source ])

        self.assertEqual(
            result, expected_result,
            "Result of \"manifest -c %s %s\" does not match expected output."
            " Expected:\n%s\nReceived:\n%s"
            % (args, source, expected_result, result)
        )

    def manifest_load_store(self, src_file):
        
        mf = Manifest()
        src_file = self.src_dir + src_file
        mf.parse_file(src_file)

        with open(src_file) as f:
            expected_result = f.read()

        output = StringIO.StringIO()
        mf.store(output)
        result = output.getvalue()
        output.close()

        self.assertEquals(
            result, expected_result,
            "Manifest load/store does not match with file %s. Received:\n%s"
            % (src_file, result)
        )

    ##### Actual tests

    def test_create_sha256(self):
        self.manifest_cli_create("-d SHA1", "manifest.SHA1.out")

    def test_create_sha512(self):
        self.manifest_cli_create("-d SHA-512", "manifest.SHA-512.out")

    def test_create_with_ignore(self):
        self.manifest_cli_create("-i example.txt -d MD5,SHA-512", "manifest.ignores.out")

    def test_load(self):
        self.manifest_load_store("manifest.SHA1.out")

    def test_load_sha512(self):
        self.manifest_load_store("manifest.SHA-512.out")
