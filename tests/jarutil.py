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
    cli_verify_jar_signature, verify, VerificationError, \
    JarSignatureMissingError, SignatureBlockFileVerificationError


class JarutilTest(TestCase):

    def cli_verify_wrap(self, jar, cert, alias):
        data = [get_data_fn(jar), get_data_fn(cert), alias]
        result = cli_verify_jar_signature(data)

        self.assertEqual(0, result,
                         "cli_verify_jar_signature() failed on %s with"
                         " certificate %s, alias %s" % (jar, cert, alias))

    def verify_wrap(self, cert, jar, key, error_prefix):
        try:
            verify(cert, jar, key)
        except VerificationError, error_message:
            self.fail("%s: %s" % (error_prefix, error_message))

    def test_cli_verify_signature_by_javatools(self):
        self.cli_verify_wrap("jarutil-signed.jar", "javatools-cert.pem",
                             "UNUSED")

    def test_cli_verify_signature_by_jarsigner(self):
        self.cli_verify_wrap("jarutil-signed-by-jarsigner.jar",
                             "javatools-cert.pem", "UNUSED")

    # Tests that signature-related files are skipped when the signature is
    # verified. The JAR file is a normal signed JAR, plus junk files with
    # "signature-related" names.
    # The test does not guarantee that no other files are skipped.
    def test_signature_related_files_skip(self):
        self.cli_verify_wrap("sig-related-junk-files.jar",
                             "javatools-cert.pem", "UNUSED")

    def test_ecdsa_pkcs8_verify(self):
        self.cli_verify_wrap("ec.jar", "ec-cert.pem", "TEST")

    def test_missing_signature_block(self):
        jar_data = get_data_fn("ec-must-fail.jar")
        cert = get_data_fn("ec-cert.pem")
        with self.assertRaises(JarSignatureMissingError):
            verify(cert, jar_data, "TEST")

    def test_tampered_signature_block(self):
        jar_data = get_data_fn("ec-tampered.jar")
        cert = get_data_fn("ec-cert.pem")
        with self.assertRaises(SignatureBlockFileVerificationError):
            verify(cert, jar_data, "TEST")


    def test_cli_sign_and_verify(self):
        src = get_data_fn("cli-sign-and-verify.jar")
        key_alias = "SAMPLE3"
        cert = get_data_fn("javatools-cert.pem")
        key = get_data_fn("javatools.pem")
        with NamedTemporaryFile() as tmp_jar:
            copyfile(src, tmp_jar.name)
            cli_sign_jar([tmp_jar.name, cert, key, key_alias])
            self.verify_wrap(cert, tmp_jar.name, key_alias,
                        "Verification of JAR which we just signed failed")


    def test_cli_sign_and_verify_ecdsa_pkcs8_sha512(self):
        src = get_data_fn("cli-sign-and-verify.jar")
        key_alias = "SAMPLE3"
        cert = get_data_fn("ec-cert.pem")
        key = get_data_fn("ec-key.pem")
        with NamedTemporaryFile() as tmp_jar:
            copyfile(src, tmp_jar.name)
            cli_sign_jar([tmp_jar.name, cert, key, key_alias])
            self.verify_wrap(cert, tmp_jar.name, key_alias,
                             "Verification of JAR which we just signed failed")


    def test_sign_with_certchain_and_verify(self):
        src = get_data_fn("certchain-data.jar")
        key_alias = "SIGNING"
        signing_cert = get_data_fn("certchain-signing.pem")
        key = get_data_fn("certchain-signing-key.pem")
        intermediate_cert = get_data_fn("certchain-intermediate.pem")
        root_cert = get_data_fn("certchain-root.pem")
        with NamedTemporaryFile() as tmp_jar:
            copyfile(src, tmp_jar.name)
            self.assertEqual(0, cli_sign_jar(
                ["-c", root_cert, "-c", intermediate_cert,
                 tmp_jar.name, signing_cert, key, key_alias]),
                "Signing with embedding a chain of certificates failed")
            self.verify_wrap(root_cert, tmp_jar.name, key_alias,
                             "Verification of JAR which we signed embedding chain of certificates failed")


#
# The end.
