"""

Simple Java Classfile unpacking module. Can be made to act an awful
lot like the javap utility included with most Java SDKs.

Most of the information used to write this was gathered from the
following web pages

http://en.wikipedia.org/wiki/Class_(file_format)
http://java.sun.com/docs/books/jvms/second_edition/html/VMSpecTOC.doc.html

author: Christopher O'Brien  <siege@preoccupied.net>

"""


# debugging mode
if False:
    def debug(*args):
        print " ".join(args)
else:
    def debug(*args):
        pass



# The constant pool types
CONST_Asciz = 1
CONST_Integer = 3
CONST_Float = 4
CONST_Long = 5
CONST_Double = 6
CONST_Class = 7
CONST_String = 8
CONST_Fieldref = 9
CONST_Methodref = 10
CONST_InterfaceMethodref = 11
CONST_NameAndType = 12



class JavaConstantPool(object):

    """ A constants pool """

    def __init__(self):
        self.consts = tuple()


    def funpack(self, buff):
        debug("unpacking constant pool")

        (count,), buff = _funpack(">H", buff)

        # first item is never present in the actual data buffer, but
        # the count number acts like it would be.
        items = [None,]
        count -= 1
    
        # two const types will "consume" an item count, but no data
        hackpass = False

        for i in xrange(0, count):

            if hackpass:
                # previous item was a long or double
                hackpass = False
                items.append((None,None))

            else:
                debug("unpacking const item %i of %i" % (i+1, count))
                item, buff = _funpack_const_item(buff)
                items.append(item)

                # if this item was a long or double, skip the next
                # counter.
                if item[0] in (CONST_Long, CONST_Double):
                    hackpass = True

        self.consts = tuple(items)
        return buff


    def get_const(self, index):
        return self.consts[index]


    def get_const_val(self, index):
        t,v = self.get_const(index)
        
        if t in (CONST_Asciz, CONST_Integer, CONST_Float):
            return v

        elif t in (CONST_Long, CONST_Double):
            return v

        elif t in (CONST_Class, CONST_String):
            return self.get_const_val(v)
        
        elif t in (CONST_Fieldref, CONST_Methodref,
                   CONST_InterfaceMethodref, CONST_NameAndType):
            return tuple([self.get_const_val(i) for i in v])
    
        else:
            raise Exception("Unknown constant pool type %i" % t)
    

    def pretty_const_comment(self, index):
        t,v = self.get_const(index)

        if t == CONST_String:
            return "\"%s\"" % repr(self.get_const_val(v))[1:-1]

        elif t == CONST_Class:
            return self.get_const_val(v)

        elif t in (CONST_Fieldref, CONST_Methodref,
                   CONST_InterfaceMethodref):

            nat = self.pretty_const_comment(v[1])
            return "%s.%s" % (self.get_const_val(v[0]), nat)

        elif t == CONST_NameAndType:
            a,b = (self.get_const_val(i) for i in v)
            if a == "<init>":
                a = self.owner.get_this()
            return "%s:%s" % (a,b)

        else:
            return ""


    def pretty_const(self, index):
        type,val = self.consts[index]

        if type is not None:
            t,v = _pretty_const_type_val(type,val)
            return "const #%i = %s\t%s;" % (index, t, v)



def _funpack_const_item(buff):

    """ unpack a constant pool item, which will consist of a type byte
    (see the CONST_ values in this module) and a value of the
    appropriate type """

    (type,),  buff = _funpack(">B", buff)

    if type == CONST_Asciz:
        (slen,), buff = _funpack(">H", buff)
        val = buff[:slen]
        buff = buffer(buff, slen)
    
    elif type == CONST_Integer:
        (val,), buff = _funpack(">i", buff)

    elif type == CONST_Float:
        (val,), buff = _funpack(">f", buff)

    elif type == CONST_Long:
        (val,), buff = _funpack(">q", buff)

    elif type == CONST_Double:
        (val,), buff = _funpack(">d", buff)

    elif type in (CONST_Class, CONST_String):
        (val,), buff = _funpack(">H", buff)

    elif type in (CONST_Fieldref, CONST_Methodref,
                  CONST_InterfaceMethodref, CONST_NameAndType):
        val, buff = _funpack(">HH", buff)

    else:
        raise Exception("unknown constant type %r" % type)

    debug("const %s\t%s;" % _pretty_const_type_val(type,val))
    return (type, val), buff



def _pretty_const_type_val(type, val):

    if type == CONST_Asciz:
        type = "Asciz"
        val = "\"%s\"" % repr(val)[1:-1]
    elif type == CONST_Integer:
        type = "Integer"
    elif type == CONST_Float:
        type = "Float"
    elif type == CONST_Long:
        type = "Long"
    elif type == CONST_Double:
        type = "Double"
    elif type == CONST_Class:
        type = "class"
        val = "#%i" % val
    elif type == CONST_String:
        type = "String"
        val = "#%i" % val
    elif type == CONST_Fieldref:
        type = "Field"
        val = "#%i.#%i" % val
    elif type == CONST_Methodref:
        type = "Method"
        val = "#%i.#%i" % val
    elif type == CONST_InterfaceMethodref:
        type = "InterfaceMethod"
        val = "#%i.#%i" % val
    elif type == CONST_NameAndType:
        type = "NameAndType"
        val = "#%i:#%i" % val
    else:
        assert(False)
    
    return type,val



class JavaAttributes(object):

    """ attributes table, as used in class, member, and code
    structures """

    def __init__(self, owner=None):
        self.attributes = tuple()
        self.attr_map = None
        
        if not owner and isinstance(self, JavaConstantPool):
            owner = self

        self.owner = owner


    def funpack(self, buff):
        debug("unpacking attributes")

        (count,), buff = _funpack(">H", buff)
        items = []

        for i in xrange(0, count):
            debug("unpacking attribute %i of %i" % (i, count))

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
        return self.get_attributes_as_map().get(name)



class JavaClassInfo(JavaConstantPool, JavaAttributes):

    """ Information from a disassembled Java class file """

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
        debug("unpacking class info")

        self.magic, buff = _funpack(">BBBB", buff)
        self.version, buff = _funpack(">HH", buff)
        buff = JavaConstantPool.funpack(self, buff)

        (self.access_flags,), buff = _funpack(">H", buff)
        (self.this_ref,), buff = _funpack(">H", buff)
        (self.super_ref,), buff = _funpack(">H", buff)

        debug("unpacking interfaces")
        (count,),buff = _funpack(">H", buff)
        self.interfaces, buff = _funpack(">%iH" % count, buff)
        
        debug("unpacking fields")
        self.fields, buff = _funpack_array(JavaMemberInfo, buff, self)

        debug("unpacking methods")
        self.methods, buff = _funpack_array(JavaMemberInfo, buff, self)

        buff = JavaAttributes.funpack(self, buff)
        
        return buff


    def get_this(self):
        return self.get_const_val(self.this_ref)


    def pretty_name(self):
        n = _pretty_class(self.get_this())
        e = _pretty_class(self.get_super())
        i = [_pretty_class(t) for t in self.get_interfaces()]
        i = ",".join(i)

        if i:
            return "%s extends %s implements %s" % (n, e, i)
        else:
            return "%s extends %s" % (n, e)


    def get_super(self):
        return self.get_const_val(self.super_ref)


    def get_interfaces(self):
        return [self.get_const_val(i) for i in self.interfaces]


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

    """ A field or method of a java class """

    def __init__(self, owner):
        JavaAttributes.__init__(self, owner)

        self.access_flags = 0
        self.name_ref = 0
        self.descriptor_ref = 0
        
        # cached unpacked attributes
        self._code = None
        self._exceptions = None
        self._cval = None


    def funpack(self, buff):
        debug("unpacking member info")

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


    def pretty_descriptor(self):
        n, t = self.get_name(), self.get_descriptor()
        
        if n == "<init>":
            n = self.owner.get_this()
            if "/" in n:
                n = n[n.rfind("/")+1:]

        pretty = _pretty_typeseq(t)
        if len(pretty) == 1:
            return "%s %s" % (pretty[0], n)
        else:
            return "%s %s%s" % (pretty[1], n, pretty[0])


    def is_method(self):
        return bool(self._code or self.get_attribute("Code"))


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

        """ the constant value of this field, or None if this is not a
        contant field """

        if self._cval is not None:
            return self._cval

        buff = self.get_attribute("ConstantValue")
        if buff is None:
            return None

        (cval_ref,) = _unpack(">H", buff)
        self._cval = self.owner.get_const_val(cval_ref)
        return self._cval



def _next_argsig(buff):
    c = buff[0]
    if c in "VZIJDF":
        return c, buffer(buff,1)
    elif c == "[":
        d,buff = _next_argsig(buffer(buff,1))
        return c+d, buff
    elif c == "L":
        s = buff[:]
        i = s.find(';')+1
        return s[:i],buffer(buff,i)
    elif c == "(":
        s = buff[:]
        i = s.find(')')+1
        return s[:i],buffer(buff,i)
    else:
        assert(False)
        


def _pretty_typeseq(s):
    at = []
    
    buff = buffer(s)
    while buff:
        t,buff = _next_argsig(buff)
        at.append(_pretty_type(t))
        
    return tuple(at)



def _pretty_type(s):
    tc = s[0]
    if tc == "(":
        args = _pretty_typeseq(s[1:-1])
        return "(%s)" % ",".join(args)
    elif tc == "V":
        return "void"
    elif tc == "Z":
        return "boolean"
    elif tc == "I":
        return "int"
    elif tc == "J":
        return "long"
    elif tc == "D":
        return "double"
    elif tc == "F":
        return "float"
    elif tc == "L":
        return _pretty_class(s[1:-1])
    elif tc == "[":
        return "%s[]" % _pretty_type(s[1:])
    else:
        assert(False)
        


def _pretty_class(s):
    return s.replace("/", ".")



class JavaCodeInfo(JavaAttributes):

    """ The 'Code' attribue of a method member of a java class """

    def __init__(self, owner):
        JavaAttributes.__init__(self, owner)

        self.max_stack = 0
        self.max_locals = 0
        self.code = None
        self.exceptions = tuple()

        # cached unpacked internals
        self._lnt = None
        self._dis = None


    def funpack(self, buff):
        debug("unpacking code info")

        (a,b,c), buff = _funpack(">HHI", buff)
        
        self.max_stack = a
        self.max_locals = b
        self.code = buffer(buff, 0, c)
        buff = buffer(buff, c)

        excps, buff = _funpack_array(JavaExceptionInfo, buff, self)
        self.exceptions = excps

        buff = JavaAttributes.funpack(self, buff)

        return buff

    
    def get_linenumbertable(self):
        if self._lnt is not None:
            return self._lnt

        buff = self.get_attribute("LineNumberTable")
        if buff is None:
            return None

        lnt = []
        (count,), buff = _funpack(">H", buff)
        for i in xrange(0, count):
            item, buff = _funpack(">HH", buff)
            lnt.append(item)

        lnt = tuple(lnt)
        self._lnt = lnt
        return lnt    


    def get_line_for_offset(self, code_offset):
        lnt = self.get_linenumbertable()

        prev = -1
        for (o,l) in lnt:
            if o < code_offset:
                prev = o
            elif o == code_offset:
                return l
            else:
                return prev

        return prev


    def disassemble(self):
        import opcodes

        if self._dis is not None:
            return self._dis

        dis = opcodes.disassemble(self.code)

        self._dis = dis
        return dis



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



def _struct_class():
    
    """ ideally, we want to use the struct.Struct class to cache compiled
    unpackers. But since that's a semi-recent addition to Python,
    we'll provide our own dummy class that presents the same interface
    but just calls the older unpack function """

    import struct

    class DummyStruct(object):
        def __init__(self, fmt):
            self.fmt = fmt
            self.size = struct.calcsize(fmt)
        def pack(self, *args):
            return struct.pack(*args)
        def unpack(self, buff):
            return struct.unpack(buff)

    if hasattr(struct, "Struct"):
        return getattr(struct, "Struct")
    else:
        return DummyStruct


MyStruct = _struct_class()
    


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
    debug("unpacked %r: %r" % (fmt, val))

    return val, buffer(buff, sfmt.size)



def _funpack_array(atype, buff, *params, **kwds):
    debug("funpack typed array")

    (count,), buff = _funpack(">H", buff)

    items = []
    for i in xrange(0, count):
        debug("unpacking typed item %i of %i" % (i+1, count))

        o  = atype(*params, **kwds)
        buff = o.funpack(buff)
        items.append(o)

    return tuple(items), buff



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
