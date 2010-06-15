"""

Simple Java Classfile unpacking module. Can be made to act an awful
lot like the javap utility included with most Java SDKs.

Most of the information used to write this was gathered from the
following web pages

http://en.wikipedia.org/wiki/Class_(file_format)
http://java.sun.com/docs/books/jvms/second_edition/html/VMSpecTOC.doc.html

author: Christopher O'Brien  <obriencj@gmail.com>

"""



# debugging mode
if False:
    def debug(*args):
        print " ".join(args)
else:
    def debug(*args):
        pass



# the four bytes at the start of every class file
JAVA_CLASS_MAGIC = (0xCA, 0xFE, 0xBA, 0xBE)
JAVA_CLASS_MAGIC_STR = "\xca\xfe\xba\xbe"



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



# class and member flags
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

    """ raised by methods that need a JavaConstantPool, but aren't
    provided one on the owning instance """

    pass



class UnpackException(Exception):

    """ raised when there is not enough data to unpack the expected
    structures """

    def __init__(self, format, wanted, present):
        self.format = format
        self.bytes_wanted = wanted
        self.bytes_present = present
        Exception.__init__("format %r requires %i bytes, only %i present" %
                           (format, wanted, present))

        
        
class Unimplemented(Exception):

    """ raised when something unexpected happens, which usually
    indicates part of the classfile specification that wasn't
    implemented in this module yet """

    pass



def memoized_getter(fun):

    """ Decorator. Records the result of a method the first time it is
    called, and returns that result thereafter rather than re-running
    the method """

    #cfn = "_" + fun.func_name
    #def memd(self):
    #    v = getattr(self, cfn, fun)
    #    if v is fun:
    #        v = fun(self)
    #        setattr(self, cfn, v)
    #    return v

    storage = [fun]
    def memd(self):
        v = storage[0]
        if v is fun:
            v = fun(self)
            storage[0] = v
        return v

    memd.func_name = fun.func_name
    memd.__doc__ = fun.__doc__
    memd.original_func = fun

    return memd



def memoized_method(fun):

    storage = {}
    def memd(self, *args):
        v = storage.get(args, fun)
        if v is fun:
            v = fun(self, *args)
            storage[args] = v
        return v

    memd.func_name = fun.func_name
    memd.__doc__ = fun.__doc__
    memd.original_func = fun

    return memd



class JavaConstantPool(object):
    
    """ A constants pool """
    

    def __init__(self):
        self.consts = []



    def unpack(self, unpacker):
 
        """ Unpacks the constant pool from an unpacker stream """

        debug("unpacking constant pool")
        
        (count,) = unpacker.unpack(">H")
        
        # first item is never present in the actual data buffer, but
        # the count number acts like it would be.
        items = [(None,None), ]
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
                item = _unpack_const_item(unpacker)
                items.append(item)

                # if this item was a long or double, skip the next
                # counter.
                if item[0] in (CONST_Long, CONST_Double):
                    hackpass = True

        self.consts = items



    def get_const(self, index):

        """ returns the type and value of the constant at index """

        return self.consts[index]



    def deref_const(self, index):

        """ returns the dereferenced value from the const pool. For
        simple types, this will be a single value indicating the
        constant. For more complex types, such as fieldref, methodref,
        etc, this will return a tuple."""

        t,v = self.consts[index]
        
        if t in (CONST_Utf8, CONST_Integer, CONST_Float,
                 CONST_Long, CONST_Double):
            return v

        elif t in (CONST_Class, CONST_String):
            return self.deref_const(v)
        
        elif t in (CONST_Fieldref, CONST_Methodref,
                   CONST_InterfaceMethodref, CONST_NameAndType):
            return tuple([self.deref_const(i) for i in v])
    
        else:
            raise Unimplemented("Unknown constant pool type %i" % t)

    

    def constants(self):

        """ sequence of tuples (index, type, dereferenced value) of
        the constant pool entries. """

        for i in xrange(1, len(self.consts)):
            t,v = self.consts[i]            
            if t:
                yield (i, t, self.deref_const(i))
    


    def pretty_constants(self):

        """ the sequence of tuples (index, pretty type, dereferenced
        value) of the constant pool entries."""

        for i in xrange(1, len(self.consts)):
            t,v = self.pretty_const(i)
            if t:
                yield (i, t, v)



    def pretty_const(self, index):
        
        """ a tuple of the pretty type and val, or (None, None) for
        invalid indexes (such as the second part of a long or double
        value) """

        t,v = self.consts[index]
        if not t:
            return None,None
        else:
            return _pretty_const_type_val(t,v)



    def pretty_const_comment(self, index):
        t,v = self.consts[index]

        if t == CONST_String:
            return "\"%s\"" % repr(self.deref_const(v))[1:-1]

        elif t == CONST_Class:
            return self.deref_const(v)

        elif t in (CONST_Fieldref, CONST_Methodref,
                   CONST_InterfaceMethodref):

            nat = self.pretty_const_comment(v[1])
            return "%s.%s" % (self.deref_const(v[0]), nat)

        elif t == CONST_NameAndType:
            a,b = (self.deref_const(i) for i in v)
            return "%s:%s" % (a,b)

        else:
            return ""



class JavaAttributes(object):

    """ attributes table, as used in class, member, and code
    structures. Requires access to a JavaConstantPool instance for
    many of its methods to work correctly. """


    def __init__(self, cpool=None):
        self.attributes = tuple()
        self.attr_map = None
        
        if not cpool and isinstance(self, JavaConstantPool):
            cpool = self

        self.cpool = cpool



    def unpack(self, unpacker):
        
        """ Unpack an attributes table from an unpacker
        stream. Modifies the structure of this instance. """

        debug("unpacking attributes")

        (count,) = unpacker.unpack(">H")
        items = []

        for i in xrange(0, count):
            debug("unpacking attribute %i of %i" % (i+1, count))

            (name, size) = unpacker.unpack(">HI")

            debug("attribute '%s', %i bytes" % (name, size))
            data = unpacker.read(size)

            items.append( (name, data) )

        self.attributes = tuple(items)



    def get_attributes_as_map(self):

        """ Requires a JavaConstantPool """

        if not self.cpool:
            raise NoPoolException("cannot dereference attribute keys")

        cval = self.cpool.deref_const
        pairs = ((cval(i),v) for (i,v) in self.attributes)
        return dict(pairs)



    def get_attribute(self, name):

        """ Requires a JavaConstantPool """

        return self.get_attributes_as_map().get(name)



class JavaClassInfo(JavaConstantPool, JavaAttributes):

    """ Information from a disassembled Java class file. """

    def __init__(self):
        JavaConstantPool.__init__(self)
        JavaAttributes.__init__(self)

        self.magic = JAVA_CLASS_MAGIC
        self.version = (0, 0)
        self.access_flags = 0
        self.this_ref = 0
        self.super_ref = 0
        self.interfaces = tuple()
        self.fields = tuple()
        self.methods = tuple()



    def unpack(self, unpacker, magic=None):

        """ Unpacks a Java class from an unpacker stream. Updates the
        structure of this instance.

        If the unpacker has already had the magic header read off of
        it, the read value may be passed via the optional magic
        parameter and it will not attempt to read the value again. """

        debug("unpacking class info")

        # only unpack the magic bytes if it wasn't specified
        magic = magic or unpacker.unpack(">BBBB")

        if isinstance(magic, str) or isinstance(magic, buffer):
            magic = tuple(ord(m) for m in magic)
        else:
            magic = tuple(magic)

        if magic != JAVA_CLASS_MAGIC:
            raise Exception("not a Java class file")

        self.magic = magic

        # unpack (minor,major), store as (major, minor)
        self.version = unpacker.unpack(">HH")[::-1]

        JavaConstantPool.unpack(self, unpacker)

        (a, b, c) = unpacker.unpack(">HHH")
        self.access_flags = a
        self.this_ref = b
        self.super_ref = c

        debug("unpacking interfaces")
        (count,) = unpacker.unpack(">H")
        self.interfaces = unpacker.unpack(">%iH" % count)
        
        debug("unpacking fields")
        self.fields = _unpack_objects(unpacker, JavaMemberInfo,
                                      self, is_method=False)
        
        debug("unpacking methods")
        self.methods = _unpack_objects(unpacker, JavaMemberInfo,
                                       self, is_method=True)

        JavaAttributes.unpack(self, unpacker)



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
        return self.deref_const(self.this_ref)


    def is_deprecated(self):
        return bool(self.get_attribute("Deprecated"))


    def get_super(self):
        return self.deref_const(self.super_ref)


    def get_interfaces(self):
        return tuple([self.deref_const(i) for i in self.interfaces])


    def get_sourcefile_ref(self):
        (r,) = _unpack(">H", self.get_attribute("SourceFile"))
        return r


    def get_sourcefile(self):
        return self.deref_const(self.get_sourcefile_ref())


    def get_source_debug_extension(self):
        buff = self.get_attribute("SourceDebugExtension")
        return (buff and str(buff)) or None


    def get_innerclasses(self):
        buff = self.get_attribute("InnerClasses")
        if buff is None:
            return None
        
        return _unpack_objects(Unpacker(buff), JavaInnerClassInfo, self)


    def get_signature(self):
        buff = self.get_attribute("Signature")
        if buff is None:
            return None

        # type index
        (ti,) = _unpack(">H", buff)

        return self.deref_const(ti)


    def get_enclosingmethod(self):
        buff = self.get_attribute("EnclosingMethod")
        if buff is None:
            return None

        # class index, method index
        (ci, mi) = _unpack(">HH", buff)
        enc_class = self.deref_const(ci)
        enc_meth,enc_type = self.deref_const(mi)

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


    def unpack(self, unpacker):

        debug("unpacking member info")

        (a, b, c) = unpacker.unpack(">HHH")

        self.access_flags = a
        self.name_ref = b
        self.descriptor_ref = c

        JavaAttributes.unpack(self, unpacker)


    def get_name(self):
        if not self.cpool:
            raise NoPoolException("cannot get Name ref")
        return self.cpool.deref_const(self.name_ref)


    def get_descriptor(self):
        if not self.cpool:
            raise NoPoolException("cannot get Descriptor ref")
        return self.cpool.deref_const(self.descriptor_ref)


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


    def get_code(self):
        buff = self.get_attribute("Code")
        if buff is None:
            return None

        if not self.cpool:
            raise NoPoolException("cannot unpack Code")

        code = JavaCodeInfo(self.cpool)
        code.unpack(Unpacker(buff))

        return code


    def get_exceptions(self):

        """ a tuple class names for the exception types this method
        may raise, or None if this is not a method"""

        buff = self.get_attribute("Exceptions")
        if buff is None:
            return ()

        excps = _unpack_array(Unpacker(buff), ">H")
        return tuple([self.cpool.deref_const(e) for e in excps])


    def get_constantvalue(self):

        """ the constant pool index for this field, or None if this is
        not a contant field"""

        buff = self.get_attribute("ConstantValue")
        if buff is None:
            return None

        (cval_ref,) = _unpack(">H", buff)
        return cval_ref


    def deref_const(self):

        """ the value at in the constant pool at the
        get_constantvalue() index """

        index = self.get_constantvalue()
        if index is None:
            return None
        else:
            return self.cpool.deref_const(index)


    def get_type_descriptor(self):

        """ the type for a field, or the return type for a method """
        
        return _typeseq(self.get_descriptor())[-1]


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


    def get_identifier(self):

        """ For methods this is the return type, the name and the
        argument descriptor. For fields it is simply the name.

        The return-type of methods is attached to the identifier due
        to the existance of bridge methods, which will technically
        allow two methods with the same name and argument type list,
        but with different return type. """

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


    def unpack(self, unpacker):

        """ Forwards and unpacks a code block from a buffer. Updates
        the internal structure of this instance, and returns the
        forwarded buffer """

        debug("unpacking code info")

        (a, b, c) = unpacker.unpack(">HHI")
        
        self.max_stack = a
        self.max_locals = b
        self.code = unpacker.read(c)

        self.exceptions = _unpack_objects(unpacker, JavaExceptionInfo, self)

        JavaAttributes.unpack(self, unpacker)

    
    def get_linenumbertable(self):

        """  a sequence of (code_offset, line_number) pairs """

        buff = self.get_attribute("LineNumberTable")
        if buff is None:
            return None

        return _unpack_array(Unpacker(buff), ">HH")


    def get_localvariabletable(self):
        
        """ a sequence of (code_offset, length, name_index,
        desc_index, index) tuples """

        buff = self.get_attribute("LocalVariableTable")
        if buff is None:
            return None

        return _unpack_array(Unpacker(buff), ">HHHHH")


    def get_localvariabletypetable(self):
        
        """ a sequence of (code_offset, length, name_index,
        signature_index, index) tuples """

        buff = self.get_attribute("LocalVariableTypeTable")
        if buff is None:
            return None

        return _unpack_array(Unpacker(buff), ">HHHHH")


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


    def unpack(self, unpacker):

        """ Forwards and unpacks an exception handler entry in an
        exception table from buff. Updates the internal structure of
        this instance and returns the forwarded buffer """

        (a, b, c, d) = unpacker.unpack(">HHHH")

        self.start_pc = a
        self.end_pc = b
        self.handler_pc = c
        self.catch_type_ref = d


    def get_catch_type(self):
        return self.cpool.deref_const(self.catch_type_ref)


    def pretty_catch_type(self):
        ct = self.get_catch_type()
        if ct:
            return "Class "+ct
        else:
            return "any"


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


    def unpack(self, unpacker):
        (a, b, c, d) = unpacker.unpack(">HHHH")
        
        self.inner_info_ref = a
        self.outer_info_ref = b
        self.name_ref = c
        self.access_flags = d


    def get_name(self):
        return self.cpool.deref_const(self.name_ref)



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
               ((50, 0), (50, 65535), "1.6"),
               ((51, 0), (51, 65535), "1.7"),
               ((52, 0), (52, 65535), "1.8") )



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


def _unpack(fmt, data):
    return Unpacker(data).unpack(fmt)



def _unpack_objects(unpacker, atype, *params, **kwds):
    (count,) = unpacker.unpack(">H")
    return unpacker.unpack_objects(count, atype, *params, **kwds)



def _unpack_array(unpacker, fmt):
    (count,) = unpacker.unpack(">H")
    return unpacker.unpack_array(count, fmt)



def _unpack_const_item(unpacker):

    """ unpack a constant pool item, which will consist of a type byte
    (see the CONST_ values in this module) and a value of the
    appropriate type """

    (typecode,) = unpacker.unpack(">B")

    if typecode == CONST_Utf8:
        (slen,) = unpacker.unpack(">H")
        val = unpacker.read(slen)
    
    elif typecode == CONST_Integer:
        (val,) = unpacker.unpack(">i")

    elif typecode == CONST_Float:
        (val,) = unpacker.unpack(">f")

    elif typecode == CONST_Long:
        (val,) = unpacker.unpack(">q")

    elif typecode == CONST_Double:
        (val,) = unpacker.unpack(">d")

    elif typecode in (CONST_Class, CONST_String):
        (val,) = unpacker.unpack(">H")

    elif typecode in (CONST_Fieldref, CONST_Methodref,
                  CONST_InterfaceMethodref, CONST_NameAndType):
        val = unpacker.unpack(">HH")

    else:
        raise Unimplemented("unknown constant type %r" % type)

    debug("const %s\t%s;" % _pretty_const_type_val(typecode,val))
    return (typecode, val)



def _pretty_const_type_val(typecode, val):

    if typecode == CONST_Utf8:
        typestr = "Asciz"
        val = repr(val)[1:-1]
    elif typecode == CONST_Integer:
        typestr = "int"
    elif typecode == CONST_Float:
        typestr = "float"
        val = "%ff" % val
    elif typecode == CONST_Long:
        typestr = "long"
        val = "%il" % val
    elif typecode == CONST_Double:
        typestr = "double"
        val = "%fd" % val
    elif typecode == CONST_Class:
        typestr = "class"
        val = "#%i" % val
    elif typecode == CONST_String:
        typestr = "String"
        val = "#%i" % val
    elif typecode == CONST_Fieldref:
        typestr = "Field"
        val = "#%i.#%i" % val
    elif typecode == CONST_Methodref:
        typestr = "Method"
        val = "#%i.#%i" % val
    elif typecode == CONST_InterfaceMethodref:
        typestr = "InterfaceMethod"
        val = "#%i.#%i" % val
    elif typecode == CONST_NameAndType:
        typestr = "NameAndType"
        val = "#%i:#%i" % val
    else:
        raise Unimplemented("unknown type, %r", typecode)
    
    return typestr,val



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



def _typeseq_iter(s):
    buff = buffer(s)
    while buff:
        t,buff = _next_argsig(buff)
        yield t


def _typeseq(s):
    return tuple(_typeseq_iter(s))
    


def _pretty_typeseq(s):
    return [_pretty_type(t) for t in _typeseq_iter(s)]



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
    
    # well that's easy.
    return s.replace("/", ".")



#
# Utility functions for unpacking shapes of binary data from a
# buffer.


def _struct_class():
    
    """ ideally, we want to use the struct.Struct class to cache
    compiled unpackers. But since that's a semi-recent addition to
    Python, we'll provide our own dummy class that presents the same
    interface but just calls the older unpack function"""

    import struct

    class Struct(object):
        def __init__(self, fmt):
            self.fmt = fmt
            self.size = struct.calcsize(fmt)
        def pack(self, *args):
            return struct.pack(*args)
        def unpack(self, buff):
            return struct.unpack(self.fmt, buff)

    # if the struct module has a Struct class, use that. Otherwise,
    # use the DummyStruct class

    if hasattr(struct, "Struct"):
        return getattr(struct, "Struct")
    else:
        return Struct



Struct = _struct_class()



class Unpacker(object):


    def __init__(self, data):
        from StringIO import StringIO

        self._cache = {}
        
        if isinstance(data, str) or isinstance(data, buffer):
            self.stream = StringIO(data)
        elif hasattr(data, "read"):
            self.stream = data
        else:
            raise TypeError("Unpacker requires a string, buffer,"
                            " or object with a read method")


    def _compile(self, fmt):
        sfmt = self._cache.get(fmt, None)
        if not sfmt:
            sfmt = Struct(fmt)
            self._cache[fmt] = sfmt
        return sfmt


    def unpack(self, fmt):
        sfmt = self._compile(fmt)
        size = sfmt.size
        buff = self.stream.read(size)
        if len(buff) < size:
            raise UnpackException(fmt, size, len(buff))
        
        val = sfmt.unpack(buff)
        return val


    def unpack_array_gen(self, count, fmt):
        for i in xrange(0, count):
            yield self.unpack(fmt)


    def unpack_array(self, count, fmt):
        return tuple(self.unpack_array_gen(count, fmt))
    

    def unpack_objects_gen(self, count, atype, *params, **kwds):
        for i in xrange(0, count):
            o = atype(*params, **kwds)
            o.unpack(self)
            yield o


    def unpack_objects(self, count, atype, *params, **kwds):
        return tuple(self.unpack_objects_gen(count, atype, *params, **kwds))


    def read(self, i):
        buff = self.stream.read(i)
        if len(buff) < i:
            raise UnpackException(None, i, len(buff))
        return buff



#
# Functions for dealing with buffers and files



def is_class(buff):

    """ checks that the data buffer has the magic numbers indicating
    it is a Java class file. Returns False if the magic numbers do not
    match, or for any errors. """

    return _unpack(">BBBB", buff) == JAVA_CLASS_MAGIC



def is_class_file(filename):
    fd = open(filename, "rb")
    c = is_class(fd.read(4))
    fd.close()
    return c == JAVA_CLASS_MAGIC_STR



def unpack_class(data, magic=None):

    """ unpacks a Java class from data, which can be a string, a
    buffer, or a stream supporting the read method. Returns a
    populated JavaClassInfo instance.

    If data is a stream which has already been confirmed to be a java
    class, it may have had the first four bytes read from it
    already. In this case, pass those bytes as a str or tuple and the
    unpacker will not attempt to read them again.
    """

    unpacker = Unpacker(data)

    magic = magic or unpacker.unpack(">BBBB")

    o = JavaClassInfo()
    o.unpack(unpacker, magic=magic)

    return o



def unpack_classfile(filename):

    """ returns a newly allocated JavaClassInfo object populated with
    the data unpacked from the specified file """

    fd = open(filename, "rb")
    ci = unpack_class(fd)
    fd.close()
    
    return ci



#
# The end.
