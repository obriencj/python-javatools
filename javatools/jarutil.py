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

from optparse import OptionParser
from shutil import copyfile
from tempfile import NamedTemporaryFile
from zipfile import ZipFile, ZIP_DEFLATED

from .manifest import file_matches_sigfile, Manifest, SignatureManifest
from .crypto import private_key_type, CannotFindKeyTypeError
from .crypto import verify_signature_block, SignatureBlockVerificationError


__all__ = (
    "cli_create_jar", "cli_sign_jar",
    "cli_verify_jar_signature", "main", )


class VerificationError(Exception):
    pass


class SignatureBlockFileVerificationError(VerificationError):
    pass


class ManifestChecksumError(VerificationError):
    pass


class JarChecksumError(VerificationError):
    pass


class JarSignatureMissingError(VerificationError):
    pass


class MissingManifestError(Exception):
    pass


def verify(certificate, jar_file):
    """
    Verifies signature of a JAR file.

    Limitations:
    - diagnostic is less verbose than of jarsigner
    :return None if verification succeeds.
    :exception SignatureBlockFileVerificationError, ManifestChecksumError,
        JarChecksumError, JarSignatureMissingError

    Reference:
    http://docs.oracle.com/javase/7/docs/technotes/guides/jar/jar.html#Signature_Validation
    Note that the validation is done in three steps. Failure at any step is a
    failure of the whole validation.
    """  # noqua

    # Step 0: get the "key alias", used also for naming of sig-related files.
    zip_file = ZipFile(jar_file)
    sf_files = filter(file_matches_sigfile, zip_file.namelist())

    if len(sf_files) == 0:
        raise JarSignatureMissingError("No .SF file in %s" % jar_file)

    elif len(sf_files) > 1:
        # This is acceptable: SF file represents a signer. But then the
        # validation logic becomes more complicated...
        msg = "Multiple .SF files in %s, this is not supported yet" % jar_file
        raise VerificationError(msg)

    sf_filename = sf_files[0]
    key_alias = sf_filename[9:-3]  # "META-INF/%s.SF"
    sf_data = zip_file.read(sf_filename)

    # Step 1: check the crypto part.
    file_list = zip_file.namelist()
    sig_block_filename = None

    # JAR specification mentions only RSA and DSA; jarsigner also has EC
    # TODO: what about "SIG-*"?
    signature_extensions = ("RSA", "DSA", "EC")
    for extension in signature_extensions:
        candidate_filename = "META-INF/%s.%s" % (key_alias, extension)
        if candidate_filename in file_list:
            sig_block_filename = candidate_filename
            break

    if sig_block_filename is None:
        msg = "None of %s found in JAR" % \
              ", ".join(key_alias + "." + x for x in signature_extensions)
        raise JarSignatureMissingError(msg)

    sig_block_data = zip_file.read(sig_block_filename)
    try:
        verify_signature_block(certificate, sf_data, sig_block_data)
    except SignatureBlockVerificationError as message:
        message = "Signature block verification failed: %s" % message
        raise SignatureBlockFileVerificationError(message)

    # KEYALIAS.SF is correctly signed.
    # Step 2: Check that it contains correct checksum of the manifest.
    signature_manifest = SignatureManifest()
    signature_manifest.parse(sf_data)

    jar_manifest = Manifest()
    jar_manifest.parse(zip_file.read("META-INF/MANIFEST.MF"))

    errors = signature_manifest.verify_manifest(jar_manifest)
    if len(errors) > 0:
        msg = "%s: in .SF file, section checksum(s) failed for: %s" \
              % (jar_file, ",".join(errors))
        raise ManifestChecksumError(msg)

    # Checksums of MANIFEST.MF itself are correct.

    # Step 3: Check that it contains valid checksums for each file
    # from the JAR.  NOTE: the check is done for JAR entries. If some
    # JAR entries are deleted after signing, the verification still
    # succeeds.  This seems to not follow the reference specification,
    # but that's what jarsigner does.
    errors = jar_manifest.verify_jar_checksums(jar_file)
    if len(errors) > 0:
        msg = "Checksum(s) for jar entries of jar file %s failed for: %s" \
              % (jar_file, ",".join(errors))
        raise JarChecksumError(msg)

    return None


def sign(jar_file, cert_file, key_file, key_alias,
         extra_certs=None, digest="SHA-256", output=None):
    """
    Signs the jar (almost) identically to jarsigner.
    :exception ManifestNotFoundError, CannotFindKeyTypeError
    :return None
    """

    jar = ZipFile(jar_file, "a")
    if "META-INF/MANIFEST.MF" not in jar.namelist():
        raise MissingManifestError(
            "META-INF/MANIFEST.MF not found in %s" % jar_file)

    mf = Manifest()
    mf.parse(jar.read("META-INF/MANIFEST.MF"))
    mf.add_jar_entries(jar_file, digest)

    # create a signature manifest, and make it match the line separator
    # style of the manifest it'll be digesting.
    sf = SignatureManifest(linesep=mf.linesep)

    sf_digest_algorithm = digest    # No point to make it different
    sf.digest_manifest(mf, sf_digest_algorithm)

    sig_digest_algorithm = digest  # No point to make it different
    sig_block_extension = private_key_type(key_file)

    sigdata = sf.get_signature(cert_file, key_file,
                               extra_certs, sig_digest_algorithm)

    # We might just add new entries to the original JAR, but jarsigner puts
    # all META-INF/ to the beginning of the archive. Let's do the same.
    with NamedTemporaryFile() as new_jar_file:
        new_jar = ZipFile(new_jar_file, "w", ZIP_DEFLATED)
        new_jar.writestr("META-INF/MANIFEST.MF", mf.get_data())
        new_jar.writestr("META-INF/%s.SF" % key_alias, sf.get_data())
        new_jar.writestr("META-INF/%s.%s" % (key_alias, sig_block_extension),
                         sigdata)
        for entry in jar.namelist():
            if not entry.upper() == "META-INF/MANIFEST.MF":
                new_jar.writestr(entry, jar.read(entry))

        new_jar.close()
        new_jar_file.flush()
        copyfile(new_jar_file.name, jar_file if output is None else output)


def create_jar(jar_file, entries):
    """
    Create JAR from given entries.
    :param jar_file: filename of the created JAR
    :type jar_file: str
    :param entries: files to put into the JAR
    :type entries: list[str]
    :return: None
    """

    # 'jar' adds separate entries for directories, also for empty ones.
    with ZipFile(jar_file, "w") as jar:
        jar.writestr("META-INF/", "")
        jar.writestr("META-INF/MANIFEST.MF", Manifest().get_data())
        for entry in entries:
            jar.write(entry)
            if os.path.isdir(entry):
                for root, dirs, files in os.walk(entry):
                    for filename in dirs + files:
                        jar.write(os.path.join(root, filename))


def cli_create_jar(argument_list):
    """
    A subset of "jar" command. Creating new JARs only.
    """

    usage_message = "usage: jarutil c [OPTIONS] file.jar files..."
    parser = OptionParser(usage=usage_message)
    parser.add_option("-m", "--main-class",
                      help="Specify application entry point")

    options, mand_args = parser.parse_args(argument_list)
    if len(mand_args) < 2:
        print usage_message
        return 1

    jar_file = mand_args[0]
    entries = mand_args[1:]
    create_jar(jar_file, entries)
    return 0


def cli_sign_jar(argument_list=None):
    """
    Command-line wrapper around sign()
    """

    usage_message = "Usage: jarutil s [OPTIONS] file.jar certificate.pem" \
                    " private_key.pem key_alias"

    parser = OptionParser(usage=usage_message)

    parser.add_option("-d", "--digest", action="store", default="SHA-256",
                      help="Digest algorithm used for signing")

    parser.add_option("-c", "--chain", action="append", default=[],
                      help="Additional certificates to embed into the"
                      " signature (PEM format). More than one can be"
                      " provided.")

    parser.add_option("-o", "--output", action="store", default=None,
                      help="Filename to put signed jar. If not provided, the"
                      " signature is added to the original jar file.")

    options, mand_args = parser.parse_args(argument_list)

    if len(mand_args) != 4:
        print usage_message
        return 1

    jar_file, cert_file, key_file, key_alias = mand_args

    try:
        sign(jar_file, cert_file, key_file, key_alias,
             options.extra_certs, options.digest, options.output)

    except CannotFindKeyTypeError:
        print "Cannot determine private key type (is it in PEM format?)"
        return 1

    except MissingManifestError:
        print "Manifest missing in jar file %s" % jar_file

    return 0


def cli_verify_jar_signature(argument_list):
    """
    Command-line wrapper around verify()
    TODO: use trusted keystore;
    """

    usage_message = "Usage: jarutil v file.jar trusted_certificate.pem"
    if len(argument_list) != 2:
        print usage_message
        return 1

    jar_file, certificate = argument_list
    try:
        verify(certificate, jar_file)
    except VerificationError as error_message:
        print error_message
        return 1
    else:
        print "Jar verified."
        return 0


def usage():
    print("Usage: jarutil [csv] [options] [argument]...")
    print("   c: create JAR from paths")
    print("   s: sign JAR")
    print("   v: verify JAR signature")
    print("Give option \"-h\" for help on particular commands.")
    return 1


def main(args):
    if len(sys.argv) < 2:
        return usage()

    # TODO: maybe use argparse for subcommands?

    command = sys.argv[1]
    rest = sys.argv[2:]

    if command == "c":
        return cli_create_jar(rest)
    elif command == "s":
        return cli_sign_jar(rest)
    elif command == "v":
        return cli_verify_jar_signature(rest)
    else:
        return usage()


#
# The end.
