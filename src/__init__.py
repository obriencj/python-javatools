"""

Simple Java Classfile unpacking module. Can be made to act an awful
lot like the javap utility included with most Java SDKs.

Most of the information used to write this was gathered from the
following web pages

http://en.wikipedia.org/wiki/Class_(file_format)
http://java.sun.com/docs/books/jvms/second_edition/html/VMSpecTOC.doc.html

author: Christopher O'Brien  <obriencj@gmail.com>

"""



# Q: What is "funpack" ?
#
# A: Any function that performs some unpacking from a buffer, then
#    returns both the unpacked data or structure, and a buffer that
#    points past the last consumed byte in unpacking. "Forward
#    Unpack". Alternately, any method which updated the structure of
#    the instance by unpacking data from the buffer, then returns the
#    forwarded buffer.



# debugging mode
if False:
    def debug(*args):
        print " ".join(args)
else:
    def debug(*args):
        pass



# The constant pool types
CONST_Utf8 = 1
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
ACC_BRIDGE = 0x0040
ACC_TRANSIENT = 0x0080
ACC_VARARGS = 0x0080
ACC_NATIVE = 0x0100
ACC_INTERFACE = 0x0200
ACC_ABSTRACT = 0x0400
ACC_STRICT = 0x0800
ACC_SYNTHETIC = 0x1000        
ACC_ANNOTATION = 0x2000
ACC_ENUM = 0x4000



class NoPoolException(Exception):
    pass


class UnpackException(Exception):
    def __init__(self, format, wanted, present):
        self.format = format
        self.bytes_wanted = wanted
        self.bytes_present = present
        Exception.__init__("format %r requires %i bytes, only %i present" %
                           (format, wanted, present))
        
        
class Unimplemented(Exception):
    pass



def memoized_getter(fun):
    cfn = "_" + fun.func_name
    def memd(self):
        v = getattr(self, cfn, fun)
        if v is fun:
            v = fun(self)
            setattr(self, cfn, v)
        return v
    memd.func_name = fun.func_name
    return memd



class JavaConstantPool(object):
    
    """ A constants pool """
    
    def __init__(self):
        self.consts = tuple()


    def funpack(self, buff):
 
        """ forward and unpack a constant pool structure from
        buff. Modifies the internal structure of this instance, and
        returns the forwarded buffer."""

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

        """ returns the value from the const pool. For simple types,
        this will be a single value indicating the constant. For more
        complex types, such as fieldref, methodref, etc, this will
        return a tuple. """

        tv = self.get_const(index)
        if not tv:
            return None

        t,v = tv
        
        if t in (CONST_Utf8, CONST_Integer, CONST_Float):
            return v

        elif t in (CONST_Long, CONST_Double):
            return v

        elif t in (CONST_Class, CONST_String):
            return self.get_const_val(v)
        
        elif t in (CONST_Fieldref, CONST_Methodref,
                   CONST_InterfaceMethodref, CONST_NameAndType):
            return tuple([self.get_const_val(i) for i in v])
    
        else:
            raise Unimplemented("Unknown constant pool type %i" % t)
    

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



class JavaAttributes(object):

    """ attributes table, as used in class, member, and code
    structures """

    def __init__(self, cpool=None):
        self.attributes = tuple()
        self.attr_map = None
        
        if not cpool and isinstance(self, JavaConstantPool):
            cpool = self

        self.cpool = cpool


    def funpack(self, buff):
        
        """ Forward and unpack an attributes table from a
        buffer. Modifies the structure of this instance, and returns
        the forwarded buffer """

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
        cp = self.cpool
        if self.attr_map is None:
            pairs = ((cp.get_const_val(i),v) for (i,v) in self.attributes)
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
        self.access_flags = 0
        self.interfaces = tuple()
        self.fields = tuple()
        self.methods = tuple()


    def funpack(self, buff):

        """ Forwards and unpacks a Java class from a buffer. Updates
        the structure of this instance, and returns the forwarded
        buffer """

        debug("unpacking class info")

        self.magic, buff = _funpack(">BBBB", buff)

        # unpack (minor,major), store as (major, minor)
        self.version, buff = _funpack(">HH", buff)
        self.version = self.version[::-1]

        buff = JavaConstantPool.funpack(self, buff)

        (self.access_flags,), buff = _funpack(">H", buff)
        (self.this_ref,), buff = _funpack(">H", buff)
        (self.super_ref,), buff = _funpack(">H", buff)

        debug("unpacking interfaces")
        (count,),buff = _funpack(">H", buff)
        self.interfaces, buff = _funpack(">%iH" % count, buff)
        
        debug("unpacking fields")
        self.fields, buff = _funpack_array(JavaMemberInfo, buff,
                                           self, is_method=False)
        
        debug("unpacking methods")
        self.methods, buff = _funpack_array(JavaMemberInfo, buff,
                                            self, is_method=True)

        buff = JavaAttributes.funpack(self, buff)
        
        return buff


    def get_field_by_name(self, name):
        for f in self.fields:
            if f.get_name() == name:
                return f
        return None


    def get_methods_by_name(self, name):
        return [m for m in self.methods if m.get_name() == name]


    def get_method_by_name_type(self, name, *argtypes):
        id = "%s(%s)" % (name, ",".join(argtypes))
        for m in self.methods:
            if m.get_identifier() == id:
                return m
        return None


    def get_major_version(self):
        return self.version[0]


    def get_minor_version(self):
        return self.version[1]


    def get_platform(self):
        return platform_from_version(*self.version)


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


    def is_annotation(self):
        return self.access_flags & ACC_ANNOTATION


    def is_enum(self):
        return self.access_flags & ACC_ENUM


    def get_this(self):
        return self.get_const_val(self.this_ref)


    def is_deprecated(self):
        return bool(self.get_attribute("Deprecated"))


    def get_super(self):
        return self.get_const_val(self.super_ref)


    @memoized_getter
    def get_interfaces(self):
        return tuple([self.get_const_val(i) for i in self.interfaces])


    @memoized_getter
    def get_sourcefile_ref(self):
        (r,) = _unpack(">H", self.get_attribute("SourceFile"))
        return r


    @memoized_getter
    def get_sourcefile(self):
        return self.get_const_val(self.get_sourcefile_ref())


    @memoized_getter
    def get_innerclasses(self):
        buff = self.get_attribute("InnerClasses")
        if buff is None:
            return None
        
        inners, buff = _funpack_array(JavaInnerClassInfo, buff, self)
        return inners


    @memoized_getter
    def get_signature(self):
        buff = self.get_attribute("Signature")
        if buff is None:
            return None

        # type index
        (ti,) = _unpack(">H", buff)

        return self.get_const_val(ti)


    @memoized_getter
    def get_enclosingmethod(self):
        buff = self.get_attribute("EnclosingMethod")
        if buff is None:
            return None

        # class index, method index
        (ci,mi) = _unpack(">HH", buff)
        enc_class = self.get_const_val(ci)
        enc_meth,enc_type = self.get_const_val(mi)

        return "%s.%s%s" % (enc_class, enc_meth, enc_type)


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
        #if self.is_super():
        #    n.append("super")
        if self.is_annotation():
            n.append("annotation")
        if self.is_enum():
            n.append("enum")

        return tuple(n)


    def pretty_this(self):
        return _pretty_class(self.get_this())


    def pretty_super(self):
        return _pretty_class(self.get_super())


    def pretty_interfaces(self):
        return [_pretty_class(t) for t in self.get_interfaces()]
    

    def pretty_descriptor(self):

        """ get the class or interface name, it's accessor flags, it's
        parent class, and any interfaces it implements"""

        f = " ".join(self.pretty_access_flags())
        if not self.is_interface():
            f += " class"

        n = self.pretty_this()
        e = self.pretty_super()
        i = ",".join(self.pretty_interfaces())

        if i:
            return "%s %s extends %s implements %s" % (f, n, e, i)
        else:
            return "%s %s extends %s" % (f, n, e)



class JavaMemberInfo(JavaAttributes):

    """ A field or method of a java class """

    def __init__(self, cpool, is_method=False):
        JavaAttributes.__init__(self, cpool)

        self.access_flags = 0
        self.name_ref = 0
        self.descriptor_ref = 0

        self.is_method = is_method


    def funpack(self, buff):

        """ Forwards and unpacks a method or field member from a
        buffer. Updates the internal structure of this instance, and
        returns the forwarded buffer. """

        debug("unpacking member info")

        (a, b, c), buff = _funpack(">HHH", buff)

        self.access_flags = a
        self.name_ref = b
        self.descriptor_ref = c
        buff = JavaAttributes.funpack(self, buff)

        return buff


    def get_name(self):
        if not self.cpool:
            raise NoPoolException("cannot get Name ref")
        return self.cpool.get_const_val(self.name_ref)


    def get_descriptor(self):
        if not self.cpool:
            raise NoPoolException("cannot get Descriptor ref")
        return self.cpool.get_const_val(self.descriptor_ref)


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


    def is_bridge(self):
        return self.access_flags & ACC_BRIDGE


    def is_varargs(self):
        return self.access_flags & ACC_VARARGS


    def is_synthetic(self):
        return ((self.access_flags & ACC_SYNTHETIC) or
                bool(self.get_attribute("Synthetic")))


    def is_enum(self):
        return self.access_flags & ACC_ENUM


    def is_deprecated(self):
        return bool(self.get_attribute("Deprecated"))


    @memoized_getter
    def get_code(self):
        buff = self.get_attribute("Code")
        if buff is None:
            return None

        if not self.cpool:
            raise NoPoolException("cannot unpack Code")

        code = JavaCodeInfo(self.cpool)
        buff = code.funpack(buff)

        return code


    @memoized_getter
    def get_exceptions(self):

        """ a tuple class names for the exception types this method
        may raise, or None if this is not a method"""

        buff = self.get_attribute("Exceptions")
        if buff is None:
            return ()

        (count,), buff = _funpack(">H", buff)
        excps, buff = _funpack(">%iH" % count, buff)

        return tuple([self.cpool.get_const_val(e) for e in excps])


    @memoized_getter
    def get_constantvalue(self):

        """ the constant pool index for this field, or None if this is
        not a contant field"""

        buff = self.get_attribute("ConstantValue")
        if buff is None:
            return None

        (cval_ref,) = _unpack(">H", buff)
        return cval_ref


    def get_const_val(self):

        """ the value at in the constant pool at the
        get_constantvalue() index """

        index = self.get_constantvalue()
        if index is None:
            return None
        else:
            return self.cpool.get_const_val(index)


    @memoized_getter
    def get_type_descriptor(self):

        """ the type for a field, or the return type for a method """
        
        return _typeseq(self.get_descriptor())[-1]


    @memoized_getter
    def get_arg_type_descriptors(self):

        """ the parameter type list for a method, or None for a field
        """

        if not self.is_method:
            # hey, we're not a method, so we don't have args
            return None

        tp = _typeseq(self.get_descriptor())
        tp = _typeseq(tp[0][1:-1])

        return tp


    def pretty_type(self):
        return _pretty_type(self.get_type_descriptor())


    def pretty_arg_types(self):
        if not self.is_method:
            return None

        pt = [_pretty_type(t) for t in self.get_arg_type_descriptors()]
        return "(%s)" % ",".join(pt)


    def pretty_descriptor(self):
        
        """ assemble a long member name from access flags, type,
        argument types, exceptions as applicable """
        
        f = " ".join(self.pretty_access_flags())
        p = self.pretty_type()
        n = self.get_name()
        a = self.pretty_arg_types()
        t = ",".join(self.pretty_exceptions())
        
        if n == "<init>":
            # rename this method to match the class name
            n = self.cpool.get_this()
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

        """ sequence of the keywords determined from the access flags"""

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
        if self.is_strict():
            n.append("strict")
        if self.is_native():
            n.append("native")
        if self.is_abstract():
            n.append("abstract")
        if self.is_enum():
            n.append("enum")

        #if self.is_synthetic():
        #    n.append("synthetic")

        if self.is_method:
            if self.is_synchronized():
                n.append("synchronized")

            #if self.is_bridge():
            #    n.append("bridge")
            #if self.is_varargs():
            #    n.append("varargs")

        else:
            if self.is_transient():
                n.append("transient")
            if self.is_volatile():
                n.append("volatile")

        return tuple(n)


    def pretty_exceptions(self):

        """ sequence of pretty names for get_exceptions() """

        return [_pretty_class(e) for e in self.get_exceptions()]


    @memoized_getter
    def get_identifier(self):

        """ for methods this is the return type, the name and the
        argument descriptor. For fields it is simply the name"""

        id = self.get_name()

        if self.is_method:
            args = ",".join(self.get_arg_type_descriptors())
            id = "%s(%s):%s" % (id, args,self.get_descriptor())

        return id



class JavaCodeInfo(JavaAttributes):

    """ The 'Code' attribue of a method member of a java class """

    def __init__(self, cpool):
        JavaAttributes.__init__(self, cpool)

        self.max_stack = 0
        self.max_locals = 0
        self.code = None
        self.exceptions = tuple()


    def funpack(self, buff):

        """ Forwards and unpacks a code block from a buffer. Updates
        the internal structure of this instance, and returns the
        forwarded buffer """

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

    
    @memoized_getter
    def get_linenumbertable(self):

        """  a sequence of (code_offset, line_number) pairs """

        buff = self.get_attribute("LineNumberTable")
        if buff is None:
            return None

        lnt = []
        (count,), buff = _funpack(">H", buff)
        for i in xrange(0, count):
            item, buff = _funpack(">HH", buff)
            lnt.append(item)

        lnt = tuple(lnt)
        return lnt


    @memoized_getter
    def get_localvariabletable(self):
        
        """ a sequence of (code_offset, length, name_index,
        desc_index, index) tuples """

        buff = self.get_attribute("LocalVariableTable")
        if buff is None:
            return None

        lvt = []
        (count,), buff = _funpack(">H", buff)
        for i in xrange(0, count):
            item, buff = _funpack(">HHHHH", buff)
            lvt.append(item)

        lvt = tuple(lvt)
        return lvt


    @memoized_getter
    def get_localvariabletypetable(self):
        
        """ a sequence of (code_offset, length, name_index,
        signature_index, index) tuples """

        buff = self.get_attribute("LocalVariableTypeTable")
        if buff is None:
            return None

        lvt = []
        (count,), buff = _funpack(">H", buff)
        for i in xrange(0, count):
            item, buff = _funpack(">HHHHH", buff)
            lvt.append(item)

        lvt = tuple(lvt)
        return lvt


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


    @memoized_getter
    def disassemble(self):
        import javaclass.opcodes as opcodes
        return opcodes.disassemble(self.code)



class JavaExceptionInfo(object):

    """ Information about an exception handler entry in an exception
    table """


    def __init__(self, code):
        self.code = code
        self.cpool = code.cpool
        
        self.start_pc = 0
        self.end_pc = 0
        self.handler_pc = 0
        self.catchx_type_ref = 0


    def funpack(self, buff):

        """ Forwards and unpacks an exception handler entry in an
        exception table from buff. Updates the internal structure of
        this instance and returns the forwarded buffer """

        (a,b,c,d), buff = _funpack(">HHHH", buff)

        self.start_pc = a
        self.end_pc = b
        self.handler_pc = c
        self.catch_type_ref = d

        return buff


    def get_catch_type(self):
        return self.cpool.get_const_val(self.catch_type_ref)


    def pretty_catch_type(self):
        ct = self.get_catch_type()
        if ct:
            return "Class "+ct
        else:
            return "any"


    @memoized_getter
    def __cmp_tuple(self):
        return (self.start_pc, self.end_pc,
                self.handler_pc, self.get_catch_type())


    def __hash__(self):
        return hash(self.__cmp_tuple())


    def __eq__(self, other):
        return self.__cmp_tuple() == other.__cmp_tuple()




class JavaInnerClassInfo(object):

    """ Information about an inner class """    

    def __init__(self, cpool):
        self.cpool = cpool

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
        return self.cpool.get_const_val(self.name_ref)



#
# Utility functions for turning major/minor versions into JVM releases
# Each entry is a tuple of minimum version and maxiumum version,
# inclusive, and the string of the platform version.

_platforms = ( ((45, 0), (45, 3), "1.0.2"),
               ((45, 4), (45, 65535), "1.1"),
               ((46, 0), (46, 65535), "1.2"),
               ((47, 0), (47, 65535), "1.3"),
               ((48, 0), (48, 65535), "1.4"),
               ((49, 0), (49, 65535), "1.5"),
               ((50, 0), (50, 65535), "1.6") )



def platform_from_version(major, minor):

    """ returns the minimum platform version that can load the given
    class version indicated by major.minor"""
    
    v = (major, minor)
    for low,high,name in _platforms:
        if low <= v <= high:
            return name
    return None



#
# Utility functions for the constants pool



def _funpack_const_item(buff):

    """ unpack a constant pool item, which will consist of a type byte
    (see the CONST_ values in this module) and a value of the
    appropriate type """

    (type,),  buff = _funpack(">B", buff)

    if type == CONST_Utf8:
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
        raise Unimplemented("unknown constant type %r" % type)

    debug("const %s\t%s;" % _pretty_const_type_val(type,val))
    return (type, val), buff



def _pretty_const_type_val(type, val):

    if type == CONST_Utf8:
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
        raise Unimplemented("unknown type, %s", type)
    
    return type,val



#
# Utility functions for dealing with exploding internal type
# signatures into sequences, and converting type signatures into
# "pretty" strings



def _next_argsig(buff):
    c = buff[0]
    if c in "VZBCSIJDF":
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
        raise Unimplemented("_next_argsig is %r in %r" % (c, buff))



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
    elif tc == "C":
        return "char"
    elif tc == "B":
        return "byte"
    elif tc == "S":
        return "short"
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
        raise Unimplemented("unknown type, %s" % tc)
        


def _pretty_class(s):
    return s.replace("/", ".")



#
# Utility functions for unpacking shapes of binary data from a
# buffer. The _funpack function is particularly important.


def _struct_class():
    
    """ ideally, we want to use the struct.Struct class to cache
    compiled unpackers. But since that's a semi-recent addition to
    Python, we'll provide our own dummy class that presents the same
    interface but just calls the older unpack function"""

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
        raise UnpackException(fmt, sfmt.size, len(buff))

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



#
# Functions for dealing with buffers and files



def is_class(buff):

    """ checks that the data buffer has the magic numbers indicating
    it is a Java class file. Returns False if the magic numbers do not
    match, or for any errors. """

    try:
        return _unpack(">BBBB", buff) == (0xCA, 0xFE, 0xBA, 0xBE)
    except:
        return False



def funpack_class(buff):

    """ forwards and unpacks a Java class from buff. Returns a tuple
    of a JavaClassInfo and the advanced buffer """

    if not is_class(buff):
        raise Exception("not a Java class file")

    o = JavaClassInfo()
    return o, o.funpack(buff)



def unpack_class(buff):

    """ returns a newly allocated JavaClassInfo object populated with
    the data unpacked from the passed buffer """

    info, buff = funpack_class(buff)
    # ignore the forwarded buff
    return info



def unpack_classfile(filename):

    """ returns a newly allocated JavaClassInfo object populated with
    the data unpacked from the specified file """

    fd = open(filename, "rb")
    data = fd.read()
    fd.close()
    
    return unpack_class(data)



#
# The end.
