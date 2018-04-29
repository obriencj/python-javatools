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
unit tests for cryptography-related functions of python-javatools.

author: Konstantin Shemyak  <konstantin@shemyak.com>
license: LGPL v.3
"""

from unittest import TestCase
from javatools.crypto import private_key_type, CannotFindKeyTypeError
from . import get_data_fn

class CryptoTest(TestCase):

    def test_private_key_type(self):
        rsa_key = get_data_fn("test_crypto/test_private_key_type__key-rsa.pem")
        self.assertEqual(private_key_type(rsa_key), "RSA")

        rsa_key_pkcs8 = get_data_fn("test_crypto/test_private_key_type__key-rsa-pkcs8.pem")
        self.assertEqual(private_key_type(rsa_key_pkcs8), "RSA")

        dsa_key = get_data_fn("test_crypto/test_private_key_type__key-dsa.pem")
        self.assertEqual(private_key_type(dsa_key), "DSA")

        ec_key = get_data_fn("test_crypto/test_private_key_type__key-ec.pem")
        self.assertEqual(private_key_type(ec_key), "EC")

        invalid_key = get_data_fn("test_crypto/test_private_key_type__key-invalid.pem")
        with self.assertRaises(CannotFindKeyTypeError):
            private_key_type(invalid_key)

#
# The end.
