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
from zipfile import ZipFile

from javatools.manifest import Manifest, SignatureManifest

__all__ = ( "cli_create_jar", "cli_check_jar", "cli_sign_jar",
            "cli_verify_jar", "cli", "main" )


def private_key_type(private_key_file):
    import subprocess
    import re

    algorithms = ("RSA", "DSA", "EC")
    # Grepping for a string will work for PKCS8 keys, but not for PKCS1.
    with open(private_key_file, "r") as f:
        # We can't just take the first line. PKCS8 may have other headers.
        for line in f:
            for algorithm in algorithms:
                if re.match("-----BEGIN %s PRIVATE KEY-----" % algorithm,
                            line):
                    return algorithm

    # No luck.
    # Anything less ugly and more efficient, but working with all key types??
    # PyOpenssl has Pkey.type()...
    with open(os.devnull, "wb") as DEVNULL:
        for algorithm in algorithms:
            if not subprocess.call(
                    ["openssl", algorithm.lower(), "-in", private_key_file],
                    stdout=DEVNULL, stderr=subprocess.STDOUT):
                return algorithm
    return None


def cli_create_jar(options, paths):
    # TODO: create a jar from paths
    return 0


def cli_sign_jar(options, jar_file, cert_file, key_file, key_alias):
    """
    Signs the jar (almost) identically to jarsigner.
    """

    jar = ZipFile(jar_file, "a")
    if not "META-INF/MANIFEST.MF" in jar.namelist():
        print "META-INF/MANIFEST.MF not found in %s" % jar_file
        return 1

    sig_block_extension = private_key_type(key_file)
    if sig_block_extension is None:
        print "Cannot determine private key type (is it in PEM format?)"
        return 1

    mf = Manifest()
    mf.parse(jar.read("META-INF/MANIFEST.MF"))

    # create a signature manifest, and make it match the line separator
    # style of the manifest it'll be digesting.
    sf = SignatureManifest(linesep=mf.linesep)

    sf_digest_algorithm = "SHA-256"
    if options and options.digest:
        sf_digest_algorithm = options.digest
    sf.digest_manifest(mf, sf_digest_algorithm)
    jar.writestr("META-INF/%s.SF" % key_alias, sf.get_data())

    sig_digest_algorithm = sf_digest_algorithm  # No point to make it different
    jar.writestr("META-INF/%s.%s" % (key_alias, sig_block_extension),
        sf.get_signature(cert_file, key_file, sig_digest_algorithm))

    return 0

def cli_verify_jar_signature(options, jarfilename, keystore=None):
    # TODO: verify the signature in a JAR matches that from a known
    # key
    return 0


def cli(parser, options, rest):
    # TODO: create, check, sign, or verify a JAR file or exploded JAR
    # directory structure
    return 0


def create_optparser():
    from optparse import OptionParser

    parser = OptionParser(usage="%prog COMMAND [OPTIONS] JARFILE [ARGUMENTS]")

    parser.add_option("-c", "--create")
    # mandatory arguments: path(s)
    # options: ignore, manifest-digest

    parser.add_option("-s", "--sign",
                      help="sign the JAR file"
                      " (must be followed with: "
                      "certificate.pem, private_key.pem, key_alias)")
    # mandatory arguments: certificate, key, alias
    # TODO: options: signature-file-digest

    parser.add_option("-v", "--verify")
    # no mandatory arguments
    # options: trusted-certificates-storage, trust-all

    return parser


def main(args):
    parser = create_optparser()
    return cli(parser, *parser.parse_args(args))


#
# The end.
