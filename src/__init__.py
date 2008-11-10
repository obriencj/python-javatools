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



ACC_PUBLIC = 0x0001
ACC_PRIVATE = 0x0002
ACC_PROTECTED = 0x0004
ACC_STATIC = 0x0008
ACC_FINAL = 0x0010
ACC_SYNCHRONIZED = 0x0020
ACC_SUPER = 0x0020
ACC_VOLATILE = 0x0040
ACC_TRANSIENT = 0x0080
ACC_NATIVE = 0x0100
ACC_INTERFACE = 0x0200
ACC_ABSTRACT = 0x0400
ACC_STRICT = 0x0800



_pretty_access_flag = {
    ACC_PUBLIC: "public",
    ACC_PRIVATE: "private",
    ACC_PROTECTED: "protected",
    ACC_STATIC: "static",
    ACC_FINAL: "final",
    ACC_SYNCHRONIZED: "synchronized",
    ACC_VOLATILE: "volatile",
    ACC_TRANSIENT: "transient",
    ACC_NATIVE: "native",
    ACC_INTERFACE: "interface",
    ACC_ABSTRACT: "abstract",
    ACC_STRICT: "strict" }
        



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
        tv = self.get_const(index)
        if not tv:
            return None

        t,v = tv
        
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


    def pretty_const_type_val(self, index):
        
        """ a tuple of the pretty type and val, or (None,None) for
        invalid indexes (such as the second part of a long or double
        value)
        """

        tv = self.get_const(index)
        if not (tv and tv[0]):
            return None,None
        else:
            return _pretty_const_type_val(*tv)



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
        val = repr(val)[1:-1]
    elif type == CONST_Integer:
        type = "int"
    elif type == CONST_Float:
        type = "float"
        val = "%ff" % val
    elif type == CONST_Long:
        type = "long"
        val = "%il" % val
    elif type == CONST_Double:
        type = "double"
        val = "%dd" % val
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


    def is_public(self):
        return self.access_flags & ACC_PUBLIC


    def is_final(self):
        return self.access_flags & ACC_FINAL


    def is_super(self):
        return self.access_flags & ACC_SUPER


    def is_interface(self):
        return self.access_flags & ACC_INTERFACE


    def is_abstract(self):
        return self.access_flags & ACC_ABSTRACT


    def get_this(self):
        return self.get_const_val(self.this_ref)


    def is_deprecated(self):
        return bool(self.get_attribute("Deprecated"))


    def pretty_access_flags(self):
        n = []
        if self.is_public():
            n.append("public")
        if self.is_final():
            n.append("final")
        if self.is_interface():
            n.append("interface")
        if self.is_abstract():
            n.append("abstract")
        return " ".join(n)


    def pretty_name(self):

        """ get the class or interface name, it's accessor flags, it's
        parent class, and any interfaces it implements"""

        f = self.pretty_access_flags()
        if not self.is_interface():
            f += " class"

        n = _pretty_class(self.get_this())
        e = _pretty_class(self.get_super())
        i = [_pretty_class(t) for t in self.get_interfaces()]
        i = ",".join(i)

        if i:
            return "%s %s extends %s implements %s" % (f, n, e, i)
        else:
            return "%s %s extends %s" % (f, n, e)


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
        self._type = None
        self._arg_types = None


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


    def pretty_type(self):
        return _pretty_type(self.get_type_descriptor())


    def pretty_arg_types(self):
        if not self.is_method():
            return None

        pt = [_pretty_type(t) for t in self.get_arg_type_descriptors()]
        return "(%s)" % ",".join(pt)


    def pretty_name(self):
        
        """ assemble a long member name from access flags, type,
        argument types, exceptions as applicable """
        
        f = self.pretty_access_flags()
        p = self.pretty_type()
        n = self.get_name()
        a = self.pretty_arg_types()
        t = ",".join(self.get_pretty_exceptions())
        
        if n == "<init>":
            # rename this method to match the class name
            n = self.owner.get_this()
            if "/" in n:
                n = n[n.rfind("/")+1:]

            # we pretend that there's no return type, even though it's V
            p = None

        if a:
            # stick the name and args together so there's no space
            n = n+a

        if t:
            # assemble any throws as necessary
            t = "throws "+t

        x = [z for z in (f,p,n,t) if z]
        return " ".join(x)


    def pretty_access_flags(self):
        n = []
        if self.is_public():
            n.append("public")
        if self.is_private():
            n.append("private")
        if self.is_protected():
            n.append("protected")
        if self.is_static():
            n.append("static")
        if self.is_final():
            n.append("final")
        if self.is_synchronized():
            n.append("synchronized")
        if self.is_native():
            n.append("native")
        if self.is_abstract():
            n.append("abstract")
        if self.is_strict():
            n.append("strict")
        if self.is_volatile():
            n.append("volatile")
        if self.is_transient():
            n.append("transient")
        return " ".join(n)


    def is_public(self):
        return self.access_flags & ACC_PUBLIC


    def is_private(self):
        return self.access_flags & ACC_PRIVATE


    def is_protected(self):
        return self.access_flags & ACC_PROTECTED


    def is_static(self):
        return self.access_flags & ACC_STATIC


    def is_final(self):
        return self.access_flags & ACC_FINAL


    def is_synchronized(self):
        return self.access_flags & ACC_SYNCHRONIZED


    def is_native(self):
        return self.access_flags & ACC_NATIVE


    def is_abstract(self):
        return self.access_flags & ACC_ABSTRACT


    def is_strict(self):
        return self.access_flags & ACC_STRICT


    def is_volatile(self):
        return self.access_flags & ACC_VOLATILE


    def is_transient(self):
        return self.access_flags & ACC_TRANSIENT


    def is_method(self):
        return bool(self._code or self.get_attribute("Code"))


    def is_deprecated(self):
        return bool(self.get_attribute("Deprecated"))


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

        """ a tuple class names for the exception types this method
        may raise, or None if this is not a method"""

        if self._exceptions is not None:
            return self._exceptions

        buff = self.get_attribute("Exceptions")
        if buff is None:
            self._exceptions = ()
            return ()

        (count,), buff = _funpack(">H", buff)
        excps, buff = _funpack(">%iH" % count, buff)

        excps = [self.owner.get_const_val(e) for e in excps]

        self._exceptions = excps
        return excps


    def get_pretty_exceptions(self):
        return [_pretty_class(e) for e in self.get_exceptions()]


    def get_constantvalue(self):

        """ the constant value of this field, or None if this is not a
        contant field """

        if self._cval is not None:
            return self._cval

        buff = self.get_attribute("ConstantValue")
        if buff is None:
            return None

        (cval_ref,) = _unpack(">H", buff)
        self._cval = cval_ref
        return cval_ref


    def get_const_val(self):
        return self.owner.get_const_val(self.get_constvalue())


    def get_type_descriptor(self):
        if self._type is None:
            self._type = _typeseq(self.get_descriptor())[-1]
        return self._type


    def get_arg_type_descriptors(self):
        if self._arg_types is not None:
            return self._arg_types

        if not self.is_method():
            return None

        tp = _typeseq(self.get_descriptor())
        tp = _typeseq(tp[0][1:-1])

        self._arg_types = tp
        return tp



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



def _typeseq(s):
    at = []
    
    buff = buffer(s)
    while buff:
        t,buff = _next_argsig(buff)
        at.append(t)
        
    return tuple(at)
    


def _pretty_typeseq(s):
    return [_pretty_type(t) for t in _typeseq(s)]



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

    def __init__(self, code):
        self.code = code
        self.owner = code.owner
        
        self.start_pc = 0
        self.end_pc = 0
        self.handler_pc = 0
        self.catchx_type_ref = 0


    def funpack(self, buff):
        (a,b,c,d), buff = _funpack(">HHHH", buff)

        self.start_pc = a
        self.end_pc = b
        self.handler_pc = c
        self.catch_type_ref = d

        return buff


    def get_catch_type(self):
        return self.owner.get_const_val(self.catch_type_ref)


    def get_pretty_catch_type(self):
        ct = self.get_catch_type()
        if ct:
            return "Class "+ct
        else:
            return "any"



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
