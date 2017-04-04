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
from shutil import copyfile, copytree, rmtree
from tempfile import NamedTemporaryFile, mkdtemp
from . import get_data_fn

from javatools.jarutil import cli_create_jar, cli_sign_jar, \
    cli_verify_jar_signature, verify, VerificationError, \
    JarSignatureMissingError, SignatureBlockFileVerificationError, \
    JarChecksumError


class JarutilTest(TestCase):

    def cli_verify_wrap(self, jar, cert):
        data = [get_data_fn(jar), get_data_fn(cert)]
        result = cli_verify_jar_signature(data)

        self.assertEqual(0, result,
                         "cli_verify_jar_signature() failed on %s with"
                         " certificate %s" % (jar, cert))

    def verify_wrap(self, cert, jar, error_prefix):
        try:
            verify(cert, jar)
        except VerificationError, error_message:
            self.fail("%s: %s" % (error_prefix, error_message))

    def test_cli_verify_signature_by_javatools(self):
        self.cli_verify_wrap("jarutil-signed.jar", "javatools-cert.pem")

    def test_cli_verify_signature_by_jarsigner(self):
        self.cli_verify_wrap("jarutil-signed-by-jarsigner.jar",
                             "javatools-cert.pem")

    # Tests that signature-related files are skipped when the signature is
    # verified. The JAR file is a normal signed JAR, plus junk files with
    # "signature-related" names.
    # The test does not guarantee that no other files are skipped.
    def test_signature_related_files_skip(self):
        self.cli_verify_wrap("sig-related-junk-files-ok.jar",
                             "javatools-cert.pem")

    def test_multiple_sf_files(self):
        jar_data = get_data_fn("multiple-sf-files.jar")
        cert = get_data_fn("javatools-cert.pem")
        with self.assertRaises(VerificationError):
            verify(cert, jar_data)

    def test_ecdsa_pkcs8_verify(self):
        self.cli_verify_wrap("ec.jar", "ec-cert.pem")

    def test_missing_signature_block(self):
        jar_data = get_data_fn("ec-must-fail.jar")
        cert = get_data_fn("ec-cert.pem")
        with self.assertRaises(JarSignatureMissingError):
            verify(cert, jar_data)

    def test_tampered_signature_block(self):
        jar_data = get_data_fn("ec-tampered.jar")
        cert = get_data_fn("ec-cert.pem")
        with self.assertRaises(SignatureBlockFileVerificationError):
            verify(cert, jar_data)

    def test_tampered_jar_entry(self):
        jar_data = get_data_fn("tampered-entry.jar")
        cert = get_data_fn("javatools-cert.pem")
        with self.assertRaises(JarChecksumError):
            verify(cert, jar_data)

    def test_several_mf_attributes(self):
        # First "x-Digest-Manifest" checksum is invalid, second is OK.
        # .SF is edited by hand, .RSA created with:
        # openssl cms -sign -binary -noattr -in META-INF/UNUSED.SF -outform der -out META-INF/UNUSED.RSA -signer tests/data/javatools-cert.pem -inkey tests/data/javatools.pem -md sha256
        self.cli_verify_wrap("several-manifest-attributes.jar",
                             "javatools-cert.pem")

    def test_main_mf_section_fails(self):
        # x-Digest-Manifest checksum is wrong,
        # but "x-Digest-Manifest-Main-Attributes is OK
        # .SF and .RSA created similarly as in test_several_mf_attributes()
        self.cli_verify_wrap("wrong-digest-manifest.jar",
                             "javatools-cert.pem")

    def test_cli_sign_and_verify(self):
        src = get_data_fn("cli-sign-and-verify.jar")
        key_alias = "SAMPLE3"
        cert = get_data_fn("javatools-cert.pem")
        key = get_data_fn("javatools.pem")
        with NamedTemporaryFile() as tmp_jar:
            copyfile(src, tmp_jar.name)
            cli_sign_jar([tmp_jar.name, cert, key, key_alias])
            self.verify_wrap(cert, tmp_jar.name,
                        "Verification of JAR which we just signed failed")


    def test_cli_sign_new_file_and_verify(self):
        src = get_data_fn("cli-sign-and-verify.jar")
        #dst = get_data_fn("tmp.jar")
        key_alias = "SAMPLE3"
        cert = get_data_fn("javatools-cert.pem")
        key = get_data_fn("javatools.pem")
        with NamedTemporaryFile() as tmp_jar, NamedTemporaryFile() as dst:
            copyfile(src, tmp_jar.name)
            cli_sign_jar([tmp_jar.name, cert, key, key_alias,
                          "-o", dst.name])
            self.verify_wrap(cert, dst.name,
                        "Verification of JAR which we just signed failed")


    def test_cli_sign_and_verify_ecdsa_pkcs8_sha512(self):
        src = get_data_fn("cli-sign-and-verify.jar")
        key_alias = "SAMPLE3"
        cert = get_data_fn("ec-cert.pem")
        key = get_data_fn("ec-key.pem")
        with NamedTemporaryFile() as tmp_jar:
            copyfile(src, tmp_jar.name)
            cli_sign_jar([tmp_jar.name, cert, key, key_alias])
            self.verify_wrap(cert, tmp_jar.name,
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
            self.verify_wrap(root_cert, tmp_jar.name,
                             "Verification of JAR which we signed embedding chain of certificates failed")


    def test_cli_create_jar(self):
        from .manifest import Manifest
        from zipfile import ZipFile

        tmp_dir = mkdtemp("-test_cli_create_jar")
        rmtree(tmp_dir)     # A better way to get name for non-existing dir?
        copytree(get_data_fn("test_cli_create"), tmp_dir)
        os.chdir(tmp_dir)
        # There seems to be no way to add empty dir to Git repo:
        os.unlink(os.path.join("example_dir", "empty_dir", "unused"))

        jar_fn = "test-cli-create.jar"

        cli_create_jar([jar_fn, "example_file", "example_dir"])
        mf = Manifest()
        with ZipFile(jar_fn) as jar_file:
            entries = jar_file.namelist()
            n_entries = len(entries)
            self.assertEqual(8, n_entries,
                             "8 entries expected in JAR, %s read" % n_entries)
            if "META-INF/MANIFEST.MF" not in entries:
                self.fail("No META-INF/MANIFEST.MF in just created JAR\n"
                          "JAR content:\n%s" % ", ".join(entries))
            mf.parse(jar_file.read("META-INF/MANIFEST.MF"))

        rmtree(tmp_dir)

        self.assertEqual(0, len(mf.sub_sections),
                         "0 subsections expected in manifest, %i found"
                         % len(mf.sub_sections))

#
# The end.
