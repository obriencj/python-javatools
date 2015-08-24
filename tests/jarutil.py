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
from shutil import copyfile
from tempfile import NamedTemporaryFile
from . import get_data_fn

from javatools.jarutil import cli_create_jar, cli_sign_jar, \
    cli_verify_jar_signature
from javatools.manifest import verify


class JarutilTest(TestCase):

    def test_cli_create_jar(self):
        self.assertEqual(0, cli_create_jar(None, "some-dir"),
                         "cli_create_jar() returned non-zero")

    def test_cli_verify_jar_signature(self):
        self.assertEqual(0, cli_verify_jar_signature(None, "file.jar"),
                         "cli_verify_jar_signature() returned non-zero")

    def test_cli_sign_and_verify(self):
        src = get_data_fn("manifest-sample3.jar")
        key_alias = "SAMPLE3"
        cert = get_data_fn("javatools-cert.pem")
        key = get_data_fn("javatools.pem")
        with NamedTemporaryFile() as tmp_jar:
            copyfile(src, tmp_jar.name)
            cli_sign_jar(None, tmp_jar.name, cert, key, key_alias)
            error_message = verify(cert, tmp_jar.name, key_alias)
            self.assertIsNone(error_message,
                              "Verification of JAR which we just signed failed: %s"
                              % error_message)

    def test_cli_sign_and_verify_ecdsa_pkcs8_sha512(self):
        key_alias = "SAMPLE3"
        cert = get_data_fn("ec-cert.pem")
        key = get_data_fn("ec-key.pem")
        with NamedTemporaryFile() as tmp_jar:
            copyfile(get_data_fn("manifest-sample3.jar"), tmp_jar.name)
            cli_sign_jar(None, tmp_jar.name, cert, key, key_alias)
            error_message = verify(cert, tmp_jar.name, key_alias)
            self.assertIsNone(error_message,
                              "Verification of JAR which we just signed failed: %s"
                              % error_message)

#
# The end.