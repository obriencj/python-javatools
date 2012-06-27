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



""" Utility module for unpacking shapes of binary data from a buffer
or stream. """



# TODO: maybe one day in the future we'll add a Packer to this. If we
# ever get to the point where we want to recompile a class from a
# JavaClassInfo instance.



def compile_struct(fmt, cache=dict()):

    """ returns a struct.Struct instance compiled from fmt. If fmt has
    already been compiled, it will return the previously compiled
    Struct instance. """

    from struct import Struct

    sfmt = cache.get(fmt, None)
    if not sfmt:
        sfmt = Struct(fmt)
        cache[fmt] = sfmt
    return sfmt



class Unpacker(object):


    """ Wraps a stream (or creates a stream for a string or buffer)
    and advances along it while unpacking structures from it.

    This class adheres to the context management protocol, so may be
    used in conjunction with the 'with' keyword """


    def __init__(self, data):
        from StringIO import StringIO

        self.stream = None
        
        if isinstance(data, str) or isinstance(data, buffer):
            self.stream = StringIO(data)
        elif hasattr(data, "read"):
            self.stream = data
        else:
            raise TypeError("Unpacker requires a string, buffer,"
                            " or object with a read method")


    def __enter__(self):
        return self


    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return (exc_type is None)


    def unpack(self, fmt):

        """ unpacks the given fmt from the underlying stream and
        returns the results. Will raise an UnpackException if there is
        not enough data to satisfy the fmt """

        sfmt = compile_struct(fmt)
        size = sfmt.size
        buff = self.stream.read(size)
        if len(buff) < size:
            raise UnpackException(fmt, size, len(buff))
        
        val = sfmt.unpack(buff)
        return val


    def _unpack_array(self, count, fmt):
        for _i in xrange(0, count):
            yield self.unpack(fmt)
    

    def unpack_array(self, fmt):
        
        """ reads a count from the unpacker, and unpacks fmt count
        times. Returns a tuple of the unpacked sequences """

        (count,) = self.unpack(">H")
        return tuple(self._unpack_array(count, fmt))


    def _unpack_objects(self, count, atype, *params, **kwds):
        for _i in xrange(0, count):
            o = atype(*params, **kwds)
            o.unpack(self)
            yield o


    def unpack_objects(self, atype, *params, **kwds):

        """ reads a count from the unpacker, and instanciates that
        many calls to atype, with the given params and kwds passed
        along. Each instance then has its unpack method called with
        this unpacker instance passed along. Returns a tuple of the
        unpacked instances """

        (count,) = self.unpack(">H")
        return tuple(self._unpack_objects(count, atype, *params, **kwds))


    def read(self, count):

        """ read count bytes from the unpacker and return it as a
        buffer """

        if not self.stream:
            raise UnpackException(None, count, 0)

        buff = self.stream.read(count)
        if len(buff) < count:
            raise UnpackException(None, count, len(buff))
        return buff


    def close(self):

        """ close this unpacker, and the underlying stream if it
        supports such """

        if hasattr(self.stream, "close"):
            self.stream.close()
        self.stream = None



class UnpackException(Exception):

    """ raised when there is not enough data to unpack the expected
    structures """

    template = "format %r requires %i bytes, only %i present"

    def __init__(self, fmt, wanted, present):
        Exception.__init__(self.template % (fmt, wanted, present))
        self.format = fmt
        self.bytes_wanted = wanted
        self.bytes_present = present



#
# The end.
