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
Cryptography-related functions for handling JAR signature block files.

:author: Konstantin Shemyak  <konstantin@shemyak.com>
:license: LGPL
"""

import sys
from subprocess import Popen, PIPE, CalledProcessError


def create_signature_block(openssl_digest, certificate, private_key, data):
    """Produces a signature block for the data.

    Executes the `openssl` binary in order to calculate
    this. TODO: replace this with M2Crypto

    References
    ----------
    http://docs.oracle.com/javase/7/docs/technotes/guides/jar/jar.html#Digital_Signatures

    :param openssl_digest: alrogithm known to OpenSSL used to digest the data
    :type openssl_digest: str
    :param certificate: filename of the certificate file (PEM format)
    :type certificate: str
    :param private_key:filename of private key used to sign (PEM format)
    :type private_key: str
    :returns: content of the signature block file as produced by jarsigner
    :rtype: str
    :raises CalledProcessError: if there was a non-zero return code from
        running the underlying openssl exec

    Note: Oracle does not specify the content of the "signature
    file block", friendly saying that "These are binary files
    not intended to be interpreted by humans".
    """

    external_cmd = "openssl cms -sign -binary -noattr -md %s" \
                   " -signer %s -inkey %s -outform der" \
                   % (openssl_digest, certificate, private_key)

    proc = Popen(external_cmd.split(),
                 stdin=PIPE, stdout=PIPE, stderr=PIPE)

    (proc_stdout, proc_stderr) = proc.communicate(input=data)

    if proc.returncode != 0:
        print proc_stderr
        raise CalledProcessError(proc.returncode, external_cmd, sys.stderr)
    else:
        return proc_stdout


def verify_signature_block(certificate_file, content_file, signature):
    """Verifies the 'signature' over the 'content' with the 'certificate'.

    :return: Error message, or None if the signature validates.
    """

    from subprocess import Popen, PIPE, STDOUT

    external_cmd = "openssl cms -verify -CAfile %s -content %s " \
                   "-inform der" % (certificate_file, content_file)

    proc = Popen(external_cmd.split(),
                 stdin=PIPE, stdout=PIPE, stderr=STDOUT)

    proc_output = proc.communicate(input=signature)[0]

    if proc.returncode != 0:
        return "Command \"%s\" returned %s: %s" \
               % (external_cmd, proc.returncode, proc_output)

    return None

#
# The end.