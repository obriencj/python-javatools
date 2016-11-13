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

from M2Crypto import SMIME, X509, BIO, RSA, DSA, EC, m2


class CannotFindKeyTypeError (Exception):
    """ Failed to determine the type of the private key.  """
    pass


def private_key_type(key_file):
    """ Determines type of the private key: RSA, DSA, EC.

    :param key_file: file path
    :type key_file: str
    :return: one of "RSA", "DSA" or "EC"
    :except CannotFindKeyTypeError
    """
    try:
        RSA.load_key(key_file)
        return "RSA"
    except:
        pass
    try:
        DSA.load_key(key_file)
        return "DSA"
    except:
        pass
    try:
        EC.load_key(key_file)
        return "EC"
    except:
        raise CannotFindKeyTypeError


def create_signature_block(openssl_digest, certificate, private_key, extra_certs, data):
    """Produces a signature block for the data.

    Reference
    ---------
    http://docs.oracle.com/javase/7/docs/technotes/guides/jar/jar.html#Digital_Signatures

    Note: Oracle does not specify the content of the "signature
    file block", friendly saying that "These are binary files
    not intended to be interpreted by humans".

    :param openssl_digest: alrogithm known to OpenSSL used to digest the data
    :type openssl_digest: str
    TODO: it is not used. M2Crypto cannot pass the signing digest.
    :param certificate: filename of the certificate file (PEM format)
    :type certificate: str
    :param private_key:filename of private key used to sign (PEM format)
    :type private_key: str
    :param extra_certs: additional certificates to embed into the signature (PEM format)
    :type param: array of filenames
    :param data: the content to be signed
    :type data: str
    :returns: content of the signature block file as produced by jarsigner
    :rtype: str
    """

    smime = SMIME.SMIME()
    smime.load_key_bio(BIO.openfile(private_key), BIO.openfile(certificate))

    if extra_certs is not None:
        # Could we use just X509.new_stack_from_der() instead?
        stack = X509.X509_Stack()
        for cert in extra_certs:
            stack.push(X509.load_cert(cert))
        smime.set_x509_stack(stack)

    pkcs7 = smime.sign(BIO.MemoryBuffer(data),
                       flags=(SMIME.PKCS7_BINARY | SMIME.PKCS7_DETACHED | SMIME.PKCS7_NOATTR))
    tmp = BIO.MemoryBuffer()
    pkcs7.write_der(tmp)
    return tmp.read()


def verify_signature_block(certificate_file, content_file, signature):
    """Verifies the 'signature' over the 'content', trusting the 'certificate'.

    :param certificate_file: the trusted certificate (PEM format)
    :type certificate_file: str
    :param content_file: The signature should match this content
    :type content_file: str
    :param signature: data (DER format) subject to check
    :type signature: str
    :return: Error message, or None if the signature validates.
    :rtype: str
    """

    sig_bio = BIO.MemoryBuffer(signature)
    pkcs7 = SMIME.PKCS7(m2.pkcs7_read_bio_der(sig_bio._ptr()), 1)
    signers_cert_stack = pkcs7.get0_signers(X509.X509_Stack())
    trusted_cert_store = X509.X509_Store()
    trusted_cert_store.load_info(certificate_file)
    smime = SMIME.SMIME()
    smime.set_x509_stack(signers_cert_stack)
    smime.set_x509_store(trusted_cert_store)
    data_bio = BIO.openfile(content_file)
    try:
        smime.verify(pkcs7, data_bio)
    except SMIME.PKCS7_Error, message:
        return "Signature verification error: %s" % message

    return None

#
# The end.

