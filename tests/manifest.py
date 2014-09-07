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


from . import get_data_fn
from javatools.manifest import main, Manifest

from cStringIO import StringIO
from unittest import TestCase
from tempfile import mkstemp


class ManifestTest(TestCase):


    def manifest_cli_create(self, args, expected_result):
        """
        execute the CLI manifest tool with the given arguments on our
        sample JAR. Verifies that the resulting output manifest is
        identical to the expected result.
        """

        # the result we expect to see from running the script
        with open(get_data_fn(expected_result)) as f:
            expected_result = f.read()

        # the invocation of the script
        src_jar = get_data_fn("manifest-sample.jar")
        tmp_out = mkstemp()[1]
        cmd = ["manifest", "-c", src_jar, "-m", tmp_out] + args.split()

        # rather than trying to actually execute the script in a
        # subprocess, we'll give it an output file call it in the
        # current process. This prevents issues when there's already
        # an installed version of python-javatools present which may
        # be down-version from the one being tested. Calling the
        # manifest utility by name will use the installed rather than
        # local dev copy. Might be able to tweak this, but for now,
        # this is safer.
        main(cmd)

        with open(tmp_out) as f:
            result = f.read()

        self.assertEqual(result, expected_result,
                         "Result of \"%r\" does not match expected output."
                         " Expected:\n%s\nReceived:\n%s"
                         % (cmd, expected_result, result))


    def manifest_load_store(self, src_file):
        """
        Loads a manifest object from a given sample in the data directory,
        then re-writes it and verifies that the result matches the
        original.
        """

        src_file = get_data_fn(src_file)

        # the expected result is identical to what we feed into the
        # manifest parser
        with open(src_file) as f:
            expected_result = f.read()

        # create a manifest and parse the chosen test data
        mf = Manifest()
        mf.parse_file(src_file)
        result = mf.get_data()

        self.assertEquals(
            result, expected_result,
            "Manifest load/store does not match with file %s. Received:\n%s"
            % (src_file, result))

        return mf


    def test_create_sha256(self):
        self.manifest_cli_create("-d SHA1", "manifest.SHA1.mf")


    def test_create_sha512(self):
        self.manifest_cli_create("-d SHA-512", "manifest.SHA-512.mf")


    def test_create_with_ignore(self):
        self.manifest_cli_create("-i example.txt -d MD5,SHA-512",
                                 "manifest.ignores.mf")


    def test_load(self):
        self.manifest_load_store("manifest.SHA1.mf")


    def test_load_sha512(self):
        self.manifest_load_store("manifest.SHA-512.mf")


    def test_load_dos_newlines(self):
        mf = self.manifest_load_store("manifest.dos-newlines.mf")
        self.assertEqual(mf.linesep, "\r\n")


#
# The end.
