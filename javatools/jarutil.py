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


__all__ = ( "cli_create_jar", "cli_check_jar", "cli_sign_jar",
            "cli_verify_jar", "cli", "main" )


def cli_create_jar(options, paths):
    # TODO: create a jar from paths
    return 0


def cli_check_jar(options, jarfilename):
    # TODO: Verify the MANIFEST.MF checksums of a JAR
    return 0


def cli_sign_jar(options, jarfilename, certfile, keyfile, alias):
    # TODO: sign a JAR and embed the signature entries
    return 0


def cli_verify_jar(options, jarfilename, keystore=None):
    # TODO: verify the signature in a JAR matches that from a known
    # key
    return 0


def cli(parser, options, rest):
    # TODO: create, check, sign, or verify a JAR file or exploded JAR
    # directory structure
    return 0


def create_optparser():
    from optparse import OptionParser

    parser = OptionParser("%prog [OPTIONS] JARFILE")

    return parser


def main(args):
    parser = create_optparser()
    return cli(parser, *parser.parse_args(args))


#
# The end.
