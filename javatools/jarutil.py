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
Module and utility for creating, modifying, signing, or verifying
Java archives

:author: Christopher O'Brien  <obriencj@gmail.com>
:license: LGPL
"""

import os
import sys
from zipfile import ZipFile

from javatools.manifest import Manifest, SignatureManifest

__all__ = ( "cli_create_jar", "cli_sign_jar",
            "cli_verify_jar_signature", "main" )


def verify(certificate, jar_file, key_alias):
    """
    Verifies signature of a JAR file.

    Limitations:
    - diagnostic is less verbose than of jarsigner
    :return: tuple (exit_status, result_message)

    Reference:
    http://docs.oracle.com/javase/7/docs/technotes/guides/jar/jar.html#Signature_Validation
    Note that the validation is done in three steps. Failure at any step is a
    failure of the whole validation.
    """

    from .crypto import verify_signature_block
    from tempfile import mkstemp

    zip_file = ZipFile(jar_file)
    sf_data = zip_file.read("META-INF/%s.SF" % key_alias)

    # Step 1: check the crypto part.
    sf_file = mkstemp()[1]
    with open(sf_file, "w") as tmp_buf:
        tmp_buf.write(sf_data)
        tmp_buf.flush()
        file_list = zip_file.namelist()
        sig_block_filename = None
        # JAR specification mentions only RSA and DSA; jarsigner also has EC
        signature_extensions = ("RSA", "DSA", "EC")
        for extension in signature_extensions:
            candidate_filename = "META-INF/%s.%s" % (key_alias, extension)
            if candidate_filename in file_list:
                sig_block_filename = candidate_filename
                break
        if sig_block_filename is None:
            return "None of %s found in JAR" % \
                   ", ".join(key_alias + "." + x for x in signature_extensions)

        sig_block_data = zip_file.read(sig_block_filename)
        error = verify_signature_block(certificate, sf_file, sig_block_data)
        os.unlink(sf_file)
        if error is not None:
            return error

    # KEYALIAS.SF is correctly signed.
    # Step 2: Check that it contains correct checksum of the manifest.
    signature_manifest = SignatureManifest()
    signature_manifest.parse(sf_data)

    jar_manifest = Manifest()
    jar_manifest.parse(zip_file.read("META-INF/MANIFEST.MF"))

    error = signature_manifest.verify_manifest_checksums(jar_manifest)
    if error is not None:
        return error

    # Checksums of MANIFEST.MF itself are correct.
    # Step 3: Check that it contains valid checksums for each file from the JAR.
    error = jar_manifest.verify_jar_checksums(jar_file)
    if error is not None:
        return error

    return None


def sign(jar_file, cert_file, key_file, key_alias, extra_certs=None, digest=None):
    """
    Signs the jar (almost) identically to jarsigner.
    """

    from .crypto import private_key_type

    jar = ZipFile(jar_file, "a")
    if "META-INF/MANIFEST.MF" not in jar.namelist():
        print "META-INF/MANIFEST.MF not found in %s" % jar_file
        return 1

    mf = Manifest()
    mf.parse(jar.read("META-INF/MANIFEST.MF"))

    # create a signature manifest, and make it match the line separator
    # style of the manifest it'll be digesting.
    sf = SignatureManifest(linesep=mf.linesep)

    sf_digest_algorithm = "SHA-256"
    sf.digest_manifest(mf, sf_digest_algorithm)
    jar.writestr("META-INF/%s.SF" % key_alias, sf.get_data())

    sig_digest_algorithm = sf_digest_algorithm  # No point to make it different
    sig_block_extension = private_key_type(key_file)

    jar.writestr("META-INF/%s.%s" % (key_alias, sig_block_extension),
        sf.get_signature(cert_file, key_file, extra_certs, sig_digest_algorithm))

    return 0


def cli_create_jar(argument_list):
    # TODO: create a jar from paths
    print "Not implemented"
    return 0


def cli_sign_jar(argument_list=None):
    """
    Command-line wrapper around sign()
    """
    from optparse import OptionParser
    from .crypto import CannotFindKeyTypeError

    usage_message = "Usage: jarutil s [OPTIONS] file.jar certificate.pem private_key.pem key_alias"

    parser = OptionParser(usage=usage_message)
    parser.add_option("-d", "--digest",
                      help="Digest algorithm used for signing   ")
    parser.add_option("-c", "--chain", action="append",
                      help="Additional certificates to embed into the signature (PEM format). More than one can be provided.")
    (options, mand_args) = parser.parse_args(argument_list)

    if len(mand_args) != 4:
        print usage_message
        return 1

    (jar_file, cert_file, key_file, key_alias) = mand_args
    digest = options.digest if options and options.digest else None
    extra_certs = options.chain if options and options.chain else None

    try:
        return sign(jar_file, cert_file, key_file, key_alias, extra_certs, digest)
    except CannotFindKeyTypeError:
        print "Cannot determine private key type (is it in PEM format?)"
        return 1


def cli_verify_jar_signature(argument_list):
    """
    Command-line wrapper around verify()
    TODO: use trusted keystore;
    """

    usage_message = "Usage: jarutil v file.jar trusted_certificate.pem key_alias"
    if len(argument_list) != 3:
        print usage_message
        return 1

    (jar_file, certificate, key_alias) = argument_list
    result_message = verify(certificate, jar_file, key_alias)
    if result_message is not None:
        print result_message
        return 1
    print "Jar verified."
    return 0


def usage():
    print("Usage: jarutil [csv] [options] [argument]...")
    print("   c: create JAR from paths (NOT IMPLEMENTED)")
    print("   s: sign JAR")
    print("   v: verify JAR signature. Arguments: file.jar trusted_certificate.pem key_alias")
    print("Give option \"-h\" for help on particular commands.")
    sys.exit(1)


def main(args):
    if len(sys.argv) < 2:
        usage()

    command = sys.argv[1]
    rest = sys.argv[2:]
    if command == "c":
        return cli_create_jar(rest)
    elif command == "s":
        return cli_sign_jar(rest)
    elif command == "v":
        return cli_verify_jar_signature(rest)
    else:
        usage()


#
# The end.
