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
:license: LGPL v.3
"""


from M2Crypto import SMIME, X509, BIO, RSA, DSA, EC, m2


class CannotFindKeyTypeError(Exception):
    """
    Failed to determine the type of the private key.
    """

    pass


class SignatureBlockVerificationError(Exception):
    """
    The Signature Block File verification failed.
    """

    pass


def private_key_type(key_file):
    """
    Determines type of the private key: RSA, DSA, EC.

    :param key_file: file path
    :type key_file: str
    :return: one of "RSA", "DSA" or "EC"
    :except CannotFindKeyTypeError
    """

    keytypes = (("RSA", RSA), ("DSA", DSA), ("EC", EC))

    for key, ktype in keytypes:
        try:
            ktype.load_key(key_file)
        except (RSA.RSAError, DSA.DSAError, ValueError):
            continue
        else:
            return key
    else:
        raise CannotFindKeyTypeError()


def create_signature_block(openssl_digest, certificate, private_key,
                           extra_certs, data):

    """
    Produces a signature block for the data.

    Reference
    ---------
    http://docs.oracle.com/javase/7/docs/technotes/guides/jar/jar.html#Digital_Signatures

    Note: Oracle does not specify the content of the "signature
    file block", friendly saying that "These are binary files
    not intended to be interpreted by humans".

    :param openssl_digest: alrogithm known to OpenSSL used to digest the data
    :type openssl_digest: str
    :param certificate: filename of the certificate file (PEM format)
    :type certificate: str
    :param private_key:filename of private key used to sign (PEM format)
    :type private_key: str
    :param extra_certs: additional certificates to embed into the signature (PEM format)
    :type extra_certs: array of filenames
    :param data: the content to be signed
    :type data: bytes
    :returns: content of the signature block file as produced by jarsigner
    :rtype: bytes
    """  # noqa

    smime = SMIME.SMIME()
    with BIO.openfile(private_key) as k, BIO.openfile(certificate) as c:
        smime.load_key_bio(k, c)

    if extra_certs is not None:
        # Could we use just X509.new_stack_from_der() instead?
        stack = X509.X509_Stack()
        for cert in extra_certs:
            stack.push(X509.load_cert(cert))
        smime.set_x509_stack(stack)

    pkcs7 = smime.sign(BIO.MemoryBuffer(data),
                       algo=openssl_digest,
                       flags=(SMIME.PKCS7_BINARY |
                              SMIME.PKCS7_DETACHED |
                              SMIME.PKCS7_NOATTR))
    tmp = BIO.MemoryBuffer()
    pkcs7.write_der(tmp)
    return tmp.read()


def ignore_missing_email_protection_eku_cb(ok, ctx):
    """
    For verifying PKCS7 signature, m2Crypto uses OpenSSL's PKCS7_verify().
    The latter requires that ExtendedKeyUsage extension, if present,
    contains 'emailProtection' OID. (Is it because S/MIME is/was the
    primary use case for PKCS7?)
    We do not want to fail the verification in this case. At present,
    M2Crypto lacks possibility of removing or modifying an existing
    extension. Let's assign a custom verification callback.
    """
    # The error we want to ignore is indicated by X509_V_ERR_INVALID_PURPOSE.
    err = ctx.get_error()
    if err != m2.X509_V_ERR_INVALID_PURPOSE:
        return ok

    # PKCS7_verify() has this requriement only for the signing certificate.
    # Do not modify the behavior for certificates upper in the chain.
    if ctx.get_error_depth() > 0:
        return ok

    # There is another cause of ERR_INVALID_PURPOSE: incompatible keyUsage.
    # Do not modify the default behavior in this case.
    cert = ctx.get_current_cert()
    try:
        key_usage = cert.get_ext('keyUsage').get_value()
        if 'digitalSignature' not in key_usage \
                and 'nonRepudiation' not in key_usage:
            return ok
    except LookupError:
        pass

    # Here, keyUsage is either absent, or contains the needed bit(s).
    # So ERR_INVALID_PURPOSE is caused by EKU not containing 'emailProtection'.
    # Ignore this error.
    return 1


def verify_signature_block(certificate_file, content, signature):
    """
    Verifies the 'signature' over the 'content', trusting the
    'certificate'.

    :param certificate_file: the trusted certificate (PEM format)
    :type certificate_file: str
    :param content: The signature should match this content
    :type content: str
    :param signature: data (DER format) subject to check
    :type signature: str
    :return None if the signature validates.
    :exception SignatureBlockVerificationError
    """

    sig_bio = BIO.MemoryBuffer(signature)
    pkcs7 = SMIME.PKCS7(m2.pkcs7_read_bio_der(sig_bio._ptr()), 1)
    signers_cert_stack = pkcs7.get0_signers(X509.X509_Stack())
    trusted_cert_store = X509.X509_Store()
    trusted_cert_store.set_verify_cb(ignore_missing_email_protection_eku_cb)
    trusted_cert_store.load_info(certificate_file)
    smime = SMIME.SMIME()
    smime.set_x509_stack(signers_cert_stack)
    smime.set_x509_store(trusted_cert_store)
    data_bio = BIO.MemoryBuffer(content)

    try:
        smime.verify(pkcs7, data_bio)
    except SMIME.PKCS7_Error as message:
        raise SignatureBlockVerificationError(message)
    else:
        return None


#
# The end.
