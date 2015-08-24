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
from javatools.manifest import main, Manifest, SignatureManifest, verify

from shutil import copyfile
from tempfile import NamedTemporaryFile
from unittest import TestCase


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
        src_jar = get_data_fn("manifest-sample1.jar")
        with NamedTemporaryFile() as tmp_out:
            cmd = ["manifest", "-c", src_jar, "-m", tmp_out.name] + args.split()

            # rather than trying to actually execute the script in a
            # subprocess, we'll give it an output file call it in the
            # current process. This prevents issues when there's already
            # an installed version of python-javatools present which may
            # be down-version from the one being tested. Calling the
            # manifest utility by name will use the installed rather than
            # local dev copy. Might be able to tweak this, but for now,
            # this is safer.
            main(cmd)
            result = tmp_out.read()

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

    def verify_signature(self, signed_jar):
        certificate = get_data_fn("javatools-cert.pem")
        jar_data = get_data_fn(signed_jar)
        error_message = verify(certificate, jar_data, "UNUSED")

        self.assertIsNone(error_message,
                          "\"%s\" verification against \"%s\" failed: %s"
                          % (jar_data, certificate, error_message))


    def test_create_sha1(self):
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


    def test_verify_signature_by_javatools(self):
        self.verify_signature("manifest-signed.jar")


    def test_verify_signature_by_jarsigner(self):
        self.verify_signature("manifest-signed-by-jarsigner.jar")

    # Tests that signature-related files are skipped when the signature is
    # verified. The JAR file is a normal signed JAR, plus junk files with
    # "signature-related" names.
    # The test does not guarantee that no other files are skipped.
    def test_signature_related_files_skip(self):
        self.verify_signature("sig-related-junk-files.jar")

    def test_cli_sign_and_verify(self):
        src = get_data_fn("manifest-sample3.jar")
        key_alias = "SAMPLE3"
        cert = get_data_fn("javatools-cert.pem")
        key = get_data_fn("javatools.pem")
        with NamedTemporaryFile() as tmp_jar:
            copyfile(src, tmp_jar.name)
            cmd = ["manifest", "-s", cert, key, key_alias, tmp_jar.name]
            self.assertEqual(main(cmd), 0, "Command %s returned non-zero status"
                             % " ".join(cmd))

            error_message = verify(cert, tmp_jar.name, key_alias)
            self.assertIsNone(error_message,
                              "Verification of JAR which we just signed failed: %s"
                              % error_message)

    def test_verify_mf_checksums_no_whole_digest(self):
        sf_file = "sf-no-whole-digest.sf"
        mf_file = "sf-no-whole-digest.mf"
        sf = SignatureManifest()
        sf.parse_file(get_data_fn(sf_file))
        mf = Manifest()
        mf.parse_file(get_data_fn(mf_file))
        error_message = sf.verify_manifest_checksums(mf)
        self.assertIsNone(error_message,
            "Verification of signature file %s against manifest %s failed: %s"
            % (sf_file, mf_file, error_message))


    def test_multi_digests(self):
        jar_file = "multi-digests.jar"

        mf_ok_file = "one-valid-digest-of-several.mf"
        mf = Manifest()
        mf.parse_file(get_data_fn(mf_ok_file))
        error_message = mf.verify_jar_checksums(get_data_fn(jar_file))
        self.assertIsNone(error_message,
            "Digest verification of %s against JAR %s failed: %s" \
            % (mf_ok_file, jar_file, error_message))

        sf_ok_file = "one-valid-digest-of-several.sf"
        sf = SignatureManifest()
        sf.parse_file(get_data_fn(sf_ok_file))
        error_message = sf.verify_manifest_checksums(mf)
        self.assertIsNone(error_message,
            "Signature file digest verification of %s against manifest %s failed: %s" \
            % (sf_ok_file, mf_ok_file, error_message))


    def test_ecdsa_pkcs8_verify(self):
        jar_data = get_data_fn("ec.jar")
        cert = get_data_fn("ec-cert.pem")
        error_message = verify(cert, jar_data, "TEST")
        self.assertIsNone(error_message,
            "Verification of JAR signed with ECDSA key failed: %s"
            % error_message)


    def test_missing_signature_block(self):
        certificate = get_data_fn("ec-cert.pem")
        jar_data = get_data_fn("ec-must-fail.jar")
        error_message = verify(certificate, jar_data, "TEST")
        self.assertIsNotNone(error_message,
            "Error: verification of non-existing key alias has succeeded")


    def test_cli_sign_and_verify_ecdsa_pkcs8_sha512(self):
        key_alias = "SAMPLE3"
        cert = get_data_fn("ec-cert.pem")
        key = get_data_fn("ec-key.pem")
        with NamedTemporaryFile() as tmp_jar:
            copyfile(get_data_fn("manifest-sample3.jar"), tmp_jar.name)
            cmd = ["manifest", "-s", "-d", "SHA-512",
                   cert, key, key_alias, tmp_jar.name]
            self.assertEqual(main(cmd), 0,
                             "Command %s returned non-zero status"
                             % " ".join(cmd))

            error_message = verify(cert, tmp_jar.name, key_alias)
            self.assertIsNone(error_message,
                              "Verification of JAR which we just signed failed: %s"
                              % error_message)
#
# The end.
