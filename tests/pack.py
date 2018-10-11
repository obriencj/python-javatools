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
unit tests for javatools.pack

author: Christopher O'Brien  <obriencj@gmail.com>
license: LGPL v.3
"""


from abc import ABCMeta, abstractmethod
from unittest import TestCase
from six import add_metaclass, BytesIO

from javatools.pack import *


@add_metaclass(ABCMeta)
class UnpackerTests(object):
    """
    Common tests for both unpacker types
    """


    @abstractmethod
    def unpacker_type(self):
        pass


    @abstractmethod
    def unpack(self, data):
        pass


    def test_type(self):
        data = b"\x05\x04\x03\x02\x01"
        up = self.unpack(data)
        self.assertEqual(type(up), self.unpacker_type())


    def test_nope(self):
        self.assertRaises(TypeError, lambda: self.unpack(5))


    def test_basics(self):
        data = b"\x05\x04\x03\x02\x01"

        with self.unpack(data) as up:

            col = up.read(1)
            self.assertEqual(col, b"\x05")

            col = up.unpack(">H")
            self.assertEqual(col, (0x0403,))

            _H = compile_struct(">H")
            col = up.unpack_struct(_H)
            self.assertEqual(col, (0x0201,))

            self.assertRaises(UnpackException, lambda: up.read(1))
            self.assertRaises(UnpackException, lambda: up.unpack(">H"))
            self.assertRaises(UnpackException, lambda: up.unpack_struct(_H))

        up = self.unpack(data)
        up.close()

        self.assertRaises(UnpackException, lambda: up.read(1))
        self.assertRaises(UnpackException, lambda: up.unpack(">H"))
        self.assertRaises(UnpackException, lambda: up.unpack_struct(_H))


    def test_array(self):
        data = "\x00\x02AB"

        self.assertEqual(len(data), 4)

        with self.unpack(data) as up:
            count,a,b = up.unpack(">HBB")
            self.assertEqual(count, 2)
            self.assertEqual(a, 65)
            self.assertEqual(b, 66)

        with self.unpack(data) as up:
            a,b = up.unpack_array(">B")
            self.assertEqual(a, (65,))
            self.assertEqual(b, (66,))

        _B = compile_struct(">B")
        with self.unpack(data) as up:
            a,b = up.unpack_struct_array(_B)
            self.assertEqual(a, (65,))
            self.assertEqual(b, (66,))


class BufferTest(UnpackerTests, TestCase):

    def unpacker_type(self):
        return BufferUnpacker


    def unpack(self, data):
        if isinstance(data, bytes):
            return unpack(data)
        elif isinstance(data, str): # Py3 here, as in Py2 str is bytes
            return unpack(data.encode('utf-8'))
        else:
            raise TypeError("This test expects instance of 'bytes' or 'str', "
                            "but {} received".format(type(data).__name__))


class StreamTest(UnpackerTests, TestCase):

    def unpacker_type(self):
        return StreamUnpacker


    def unpack(self, data):
        if isinstance(data, bytes):
            return unpack(BytesIO(data))
        elif isinstance(data, str): # Py3 here, as in Py2 str is bytes
            return unpack(BytesIO(data.encode('utf-8')))
        else:
            raise TypeError("This test expects instance of 'bytes' or 'str', "
                            "but {} received".format(type(data).__name__))

#
# The end.
