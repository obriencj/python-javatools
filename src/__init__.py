"""

Simple Java Classfile unpacking module. Can be made to act an awful
lot like the javap utility included with most Java SDKs.

Most of the information used to write this was gathered from the
following web pages

http://en.wikipedia.org/wiki/Class_(file_format)
http://java.sun.com/docs/books/jvms/second_edition/html/VMSpecTOC.doc.html

author: Christopher O'Brien  <siege@preoccupied.net>

"""



class JavaClassInfo(object):
    def __init__(self):
        self.magic = 0
        self.version = (0,0)
        self.consts = tuple()
        self.interfaces = tuple()
        self.fields = tuple()
        self.methods = tuple()
        self.attributes = {}
        self.attr_map = None

        self.sourcefile_ref = 0
    

    def pretty_const(self, i):
        t,v = pretty_type_val(*self.consts[i])
        return "const #%i = %s\t%s;" % (i, t, v)


    def pretty(self):
        pass
        

    def print_consts(self):
        for i in xrange(1, len(self.consts)):
            print self.pretty_const(i)


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


    def get_attributes_as_map(self):
        if self.attr_map is None:
            pairs = ((self.get_const_val(i),v) for (i,v) in self.attributes)
            self.attr_map = dict(pairs)

        return self.attr_map


    def get_attribute(self, name):
        return self.get_attributes_as_map()[name]


    def get_sourcefile(self):
        if self.sourcefile_ref == 0:
            (r,) = _unpack(">H", self.get_attribute("SourceFile"))
            self.sourcefile_ref = r
            
        return self.get_const_val(self.sourcefile_ref)


    def get_innerclasses(self):
        inner = self.get_attribute("InnerClasses")
        if inner is None:
            return None

        # todo: unpack into tuple of JavaInnerClass
        pass



class JavaMemberInfo(object):
    def __init__(self):
        self.access_flags = 0
        self.name_ref = 0
        self.descriptor_ref = 0
        self.attributes = tuple()

        self.owner = None
        self.attr_map = None


    def pretty(self):
        pass


    def get_name(self):
        if not self.owner:
            raise Exception("member has no owner")
        return self.owner.get_const_val(self.name_ref)


    def get_descriptor(self):
        if not self.owner:
            raise Exception("memeber has no owner")
        return self.owner.get_const_val(self.descriptor_ref)


    def get_attributes_as_map(self):
        if not self.owner:
            raise Exception("memeber has no owner")

        if self.attr_map is None:
            o = self.owner
            pairs = ((o.get_const_val(i),v) for (i,v) in self.attributes)
            self.attr_map = dict(pairs)

        return self.attr_map


    def get_attribute(self, name):
        return self.get_attributes_as_map().get(name)


    def get_code(self):
        code = self.get_attribute("Code")
        if code is None:
            return None

        # todo: unpack into a JavaCode
        pass


    def get_exceptions(self):
        excp = self.get_attribute("Exceptions")
        if excp is None:
            return None

        # todo: unpack into tuple of JavaException
        pass


    def get_constvalue(self):
        cval = self.get_attribute("ConstantValue")
        if cval is None:
            return None

        # todo: unpack into a JavaConstValue
        pass



def pretty_type_val(type, val):
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

    return (type, val)



def _compile(fmt):

    """ just a cache of Struct instances """

    import struct

    sfmt = _compile.cache.get(fmt, None)
    if not sfmt:
        sfmt = struct.Struct(fmt)
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



def is_class(buff):

    """ checks that the data buffer has the magic numbers indicating
    it is a Java class file. Returns False if the magic numbers do not
    match, or for any errors. """

    try:
        return _unpack("BBBB", buff) == (0xCA, 0xFE, 0xBA, 0xBE)
    except:
        return False



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



def _funpack_consts(buff):
    (count,), buff = _funpack(">H", buff)
    items = [None,]
    
    for i in xrange(1, count):
        item, buff = _funpack_const_item(buff)
        items.append(item)

    return tuple(items), buff



def _funpack_interfaces(buff):
    (count,), buff = _funpack(">H", buff)
    items = []

    for i in xrange(0, count):
        (item,), buff = _funpack(">H", buff)
        items.append(item)

    return tuple(items), buff



def _funpack_attributes(buff):
    (count,), buff = _funpack(">H", buff)
    items = []

    for i in xrange(0, count):
        (name, size,), buff = _funpack(">HI", buff)
        data = buffer(buff, 0, size)
        buff = buffer(buff, size)
        items.append( (name, data) )

    return tuple(items), buff



def _funpack_member_info(buff):
    f = JavaMemberInfo()

    (a, b, c), buff = _funpack(">HHH", buff)
    f.access_flags = a
    f.name_ref = b
    f.descriptor_ref = c
    f.attributes, buff = _funpack_attributes(buff)

    return f, buff



def _funpack_members(buff, owner=None):
    (count,), buff = _funpack(">H", buff)
    items = []

    for i in xrange(0, count):
        field, buff = _funpack_member_info(buff)
        field.owner = owner
        items.append(field)

    return tuple(items), buff



def unpack_class(buff):
    if not is_class(buff):
        raise Exception("not a Java class file")

    o = JavaClassInfo()

    o.magic, buff = _funpack("BBBB", buff)
    o.version, buff = _funpack(">HH", buff)
    o.consts, buff = _funpack_consts(buff)
    (o.access_flags,), buff = _funpack(">H", buff)
    (o.this_ref,), buff = _funpack(">H", buff)
    (o.super_ref,), buff = _funpack(">H", buff)
    o.interfaces, buff = _funpack_interfaces(buff)
    o.fields, buff = _funpack_members(buff, owner=o)
    o.methods, buff = _funpack_members(buff, owner=o)
    o.attributes, buff = _funpack_attributes(buff)

    return o



def unpack_classfile(filename):
    fd = open(filename, "rb")
    data = fd.read()
    fd.close()
    
    return unpack_class(data)



#
# The end.
