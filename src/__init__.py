"""

Simple Java Classfile unpacking module. Can be made to act an awful
lot like the javap utility included with most Java SDKs.

Most of the information used to write this was gathered from the
following web pages

http://en.wikipedia.org/wiki/Class_(file_format)
http://java.sun.com/docs/books/jvms/second_edition/html/VMSpecTOC.doc.html

author: Christopher O'Brien  <siege@preoccupied.net>

"""



class JavaConstantPool(object):

    def __init__(self):
        self.consts = tuple()


    def funpack(self, buff):
        (count,), buff = _funpack(">H", buff)
        items = [None,]
    
        for i in xrange(1, count):
            item, buff = _funpack_const_item(buff)
            items.append(item)
        
        self.consts = tuple(items)
        return buff


    def get_const(self, index):
        return self.consts[index]


    def get_const_val(self, index):
        t,v = self.get_const(index)
        
        if t in (1,3,4):
            return v

        elif t == 5:
            t2,v2 = self.get_const(index+1)

        elif t == 6:
            t2,v2 = self.get_const(index+1)

        elif t in (7,8):
            return self.get_const_val(v)
        
        elif t in (9,10,11,12):
            return tuple([self.get_const_val(i) for i in v])


    def pretty_const(self, index):
        type,val = self.consts[index]

        if type == 1:
            type = "Asciz"
            val = str(val)
        elif type == 3:
            type = "Integer"
        elif type == 4:
            type = "Float"
        elif type == 5:
            type = "Long"
        elif type == 6:
            type = "Double"
        elif type == 7:
            type = "class"
            val = "#%i" % val
        elif type == 8:
            type = "String"
            val = "#%i" % val
        elif type == 9:
            type = "Field"
            val = "#%i.#%i" % val
        elif type == 10:
            type = "Method"
            val = "#%i.#%i" % val
        elif type == 11:
            type = "InterfaceMethod"
            val = "#%i.#%i" % val
        elif type == 12:
            type = "NameAndType"
            val = "#%i:#%i" % val

        return "const #%i = %s\t%s;" % (index, type, val)


    def print_consts(self):
        for i in xrange(1, len(self.consts)):
            print self.pretty_const(i)



class JavaAttributes(object):

    def __init__(self, owner=None):
        self.attributes = tuple()
        self.attr_map = None
        
        if not owner and isinstance(self, JavaConstantPool):
            owner = self

        self.owner = owner


    def funpack(self, buff):
        (count,), buff = _funpack(">H", buff)
        items = []

        for i in xrange(0, count):
            (name, size,), buff = _funpack(">HI", buff)
            data = buffer(buff, 0, size)
            buff = buffer(buff, size)
            items.append( (name, data) )

        self.attributes = tuple(items)
        return buff


    def get_attributes_as_map(self):
        o = self.owner
        if self.attr_map is None:
            pairs = ((o.get_const_val(i),v) for (i,v) in self.attributes)
            self.attr_map = dict(pairs)

        return self.attr_map


    def get_attribute(self, name):
        return self.get_attributes_as_map()[name]



class JavaClassInfo(JavaConstantPool, JavaAttributes):
    def __init__(self):
        JavaConstantPool.__init__(self)
        JavaAttributes.__init__(self)

        self.magic = 0
        self.version = (0,0)
        self.interfaces = tuple()
        self.fields = tuple()
        self.methods = tuple()

        # cached unpacked attributes
        self._sourcefile_ref = 0
        self._inners = None


    def funpack(self, buff):

        self.magic, buff = _funpack(">BBBB", buff)
        self.version, buff = _funpack(">HH", buff)
        buff = JavaConstantPool.funpack(self, buff)
        (self.access_flags,), buff = _funpack(">H", buff)
        (self.this_ref,), buff = _funpack(">H", buff)
        (self.super_ref,), buff = _funpack(">H", buff)

        (count,),buff = _funpack(">H", buff)
        self.interfaces, buff = _funpack(">%iH" % count, buff)
        
        self.fields, buff = _funpack_array(JavaMemberInfo, buff, self)
        self.methods, buff = _funpack_array(JavaMemberInfo, buff, self)

        buff = JavaAttributes.funpack(self, buff)
        
        return buff


    def get_sourcefile(self):
        if self._sourcefile_ref == 0:
            (r,) = _unpack(">H", self.get_attribute("SourceFile"))
            self._sourcefile_ref = r
            
        return self.get_const_val(self._sourcefile_ref)


    def get_innerclasses(self):
        if self._inners is not None:
            return self._inners

        buff = self.get_attribute("InnerClasses")
        if buff is None:
            return None
        
        inners, buff = _funpack_array(JavaInnerClassInfo, buff, self)

        self._inners = inners
        return inners



class JavaMemberInfo(JavaAttributes):
    def __init__(self, owner):
        JavaAttributes.__init__(self, owner)

        self.access_flags = 0
        self.name_ref = 0
        self.descriptor_ref = 0
        
        # cached unpacked attributes
        self._code = None
        self._exceptions = None


    def funpack(self, buff):
        (a, b, c), buff = _funpack(">HHH", buff)

        self.access_flags = a
        self.name_ref = b
        self.descriptor_ref = c
        buff = JavaAttributes.funpack(self, buff)

        return buff


    def get_name(self):
        if not self.owner:
            raise Exception("member has no owning class")
        return self.owner.get_const_val(self.name_ref)


    def get_descriptor(self):
        if not self.owner:
            raise Exception("memeber has no owning class")
        return self.owner.get_const_val(self.descriptor_ref)


    def get_code(self):
        if self._code is not None:
            return self._code

        buff = self.get_attribute("Code")
        if buff is None:
            return None

        if not self.owner:
            raise Exception("memeber has no owning class")

        code = JavaCodeInfo(self.owner)
        buff = code.funpack(buff)

        self._code = code
        return code


    def get_exceptions(self):

        """ a tuple of index ref to the contant pool of the exception types
        this method may raise, or None if this is not a method """

        if self._exceptions is not None:
            return self._exceptions

        buff = self.get_attribute("Exceptions")
        if buff is None:
            return None

        (count,), buff = _funpack(">H", buff)
        excps, buff = _funpack(">%iH" % count, buff)

        self._exceptions = excps
        return excps


    def get_constvalue(self):

        """ an index ref of the constant pool to the constant value of this
        field, or None if this is not a contant field """

        buff = self.get_attribute("ConstantValue")
        if buff is None:
            return None

        (cval_ref,) = _unpack(">H", buff)
        return cval_ref



class JavaCodeInfo(JavaAttributes):

    def __init__(self, owner):
        JavaAttributes.__init__(self, owner)

        self.max_stack = 0
        self.max_locals = 0
        self.code = None
        self.exceptions = tuple()


    def funpack(self, buff):
        (a,b,c), buff = _funpack(">HHI", buff)
        
        self.max_stack = a
        self.max_locals = b
        self.code = buffer(buff, 0, c)
        buff = buffer(buff, c)

        excps, buff = _funpack_array(JavaExceptionInfo, buff, self)
        self.exceptions = excps

        buff = JavaAttributes.funpack(self, buff)

        return buff



class JavaExceptionInfo(object):

    def __init__(self, owner):
        self.owner = owner
        
        self.start_pc = 0
        self.end_pc = 0
        self.handler_pc = 0
        self.catch_type_ref = 0


    def funpack(self, buff):
        (a,b,c,d), buff = _funpack(">HHHH", buff)

        self.start_pc = a
        self.end_pc = b
        self.handler_pc = c
        self.catch_type_ref = d

        return buff


    def get_catch_type(self):
        return self.owner.get_const_val(self.catch_type_ref)



class JavaInnerClassInfo(object):

    def __init__(self, owner):
        self.owner = owner

        self.inner_info_ref = 0
        self.outer_info_ref = 0
        self.name_ref = 0
        self.access_flags = 0


    def funpack(self, buff):
        (a,b,c,d), buff = _funpack(">HHHH", buff)
        
        self.inner_info_ref = a
        self.outer_info_ref = b
        self.name_ref = c
        self.access_flags = d

        return buff


    def get_name(self):
        return self.owner.get_const_val(self.name_ref)



def struct_class():
    
    """ ideally, we want to use the struct.Struct class to cache compiled
    unpackers. But since that's a semi-recent addition to Python,
    we'll provide our own dummy class that presents the same interface
    but just calls the older unpack function """

    import struct

    class DummyStruct(object):
        def __init__(self, fmt):
            self.fmt = fmt
            self.size = struct.calcsize(fmt)
        def unpack(self, buff):
            return struct.unpack(buff)

    if hasattr(struct, "Struct"):
        return getattr(struct, "Struct")
    else:
        return DummyStruct


MyStruct = struct_class()
    


def _compile(fmt):

    """ just a cache of Struct instances """

    sfmt = _compile.cache.get(fmt, None)
    if not sfmt:
        sfmt = MyStruct(fmt)
        _compile.cache[fmt] = sfmt
    return sfmt

_compile.cache = {}



def _unpack(fmt, buff):

    """ returns a tuple of unpacked data. Behaves almost identical to
    struct.unpack but is more lenient towards too-long data """

    return _funpack(fmt, buff)[0]



def _funpack(fmt, buff):
    
    """ forward and unpack. returns a tuple of the unpacked data
    (which is itself a tuple) and a buffer advanced past the bytes
    used to unpack said data """
    
    sfmt = _compile(fmt)

    if len(buff) < sfmt.size:
        raise Exception("not enough data in buffer for format")

    pbuff = buffer(buff, 0, sfmt.size)
    val = sfmt.unpack(pbuff)
    #print "unpacked %r: %r" % (fmt, val)

    return val, buffer(buff, sfmt.size)



def _funpack_array(atype, buff, *params, **kwds):
    (count,), buff = _funpack(">H", buff)

    items = []
    for i in xrange(0, count):
        o  = atype(*params, **kwds)
        buff = o.funpack(buff)
        items.append(o)

    return tuple(items)



def _funpack_const_item(buff):
    (type,),  buff = _funpack(">B", buff)

    if type == 1:
        (slen,), buff = _funpack(">H", buff)
        val = buffer(buff, 0, slen)
        val = str(val) # meh.
        buff = buffer(buff, slen)
    
    elif type == 3:
        (val,), buff = _funpack(">i", buff)

    elif type == 4:
        (val,), buff = _funpack(">f", buff)

    elif type in (5, 6):
        (val,), buff = _funpack(">I", buff)

    elif type in (7, 8):
        (val,), buff = _funpack(">H", buff)

    elif type in (9, 10, 11, 12):
        val, buff = _funpack(">HH", buff)

    else:
        raise Exception("unknown constant type %r" % type)

    return (type, val), buff



def is_class(buff):

    """ checks that the data buffer has the magic numbers indicating
    it is a Java class file. Returns False if the magic numbers do not
    match, or for any errors. """

    try:
        return _unpack(">BBBB", buff) == (0xCA, 0xFE, 0xBA, 0xBE)
    except:
        return False



def funpack_class(buff):
    if not is_class(buff):
        raise Exception("not a Java class file")

    o = JavaClassInfo()
    return o, o.funpack(buff)



def unpack_class(buff):
    info, buff = funpack_class(buff)
    return info



def unpack_classfile(filename):
    fd = open(filename, "rb")
    data = fd.read()
    fd.close()
    
    return unpack_class(data)



#
# The end.
