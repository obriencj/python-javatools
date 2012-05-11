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
Simple Java Classfile unpacking module. Can be made to act an awful
lot like the javap utility included with most Java SDKs.

Most of the information used to write this was gathered from the
following web pages

http://en.wikipedia.org/wiki/Class_(file_format)
http://java.sun.com/docs/books/jvms/second_edition/html/VMSpecTOC.doc.html

author: Christopher O'Brien  <obriencj@gmail.com>
license: LGPL
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
CONST_ModuleIdInfo = 13



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
ACC_MODULE = 0x8000



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
    implemented in this module yet"""

    pass



def memoized_getter(fun):

    """ Decorator. Records the result of a method the first time it is
    called, and returns that result thereafter rather than re-running
    the method"""

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

        if not index:
            raise Exception("Requested const 0")

        t,v = self.consts[index]
        
        if t in (CONST_Utf8, CONST_Integer, CONST_Float,
                 CONST_Long, CONST_Double):
            return v

        elif t in (CONST_Class, CONST_String):
            return self.deref_const(v)
        
        elif t in (CONST_Fieldref, CONST_Methodref,
                   CONST_InterfaceMethodref, CONST_NameAndType,
                   CONST_ModuleIdInfo):
            return tuple([self.deref_const(i) for i in v])
    
        else:
            raise Unimplemented("Unknown constant pool type %r" % t)

    

    def constants(self):

        """ sequence of tuples (index, type, dereferenced value) of
        the constant pool entries. """

        for i in xrange(1, len(self.consts)):
            t,v = self.consts[i]            
            if t:
                yield (i, t, self.deref_const(i))
    


    def pretty_constants(self):

        """ the sequence of tuples (index, pretty type, value) of the
        constant pool entries."""

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



    def pretty_deref_const(self, index):
        t,v = self.consts[index]

        if t == CONST_String:
            return "%s" % repr(self.deref_const(v))[1:-1]

        elif t == CONST_Class:
            return _pretty_class(self.deref_const(v))

        elif t == CONST_Fieldref:
            cn = self.deref_const(v[0])
            cn = _pretty_class(cn)

            n,t = self.deref_const(v[1])

            return "%s.%s:%s" % (cn, n, _pretty_type(t))

        elif t in (CONST_Methodref,
                   CONST_InterfaceMethodref):
            
            cn = self.deref_const(v[0])
            cn = _pretty_class(cn)

            n,t = self.deref_const(v[1])

            args,ret = tuple(_pretty_typeseq(t))

            return "%s.%s%s:%s" % (cn, n, args, ret)

        elif t == CONST_NameAndType:
            a,b = (self.deref_const(i) for i in v)
            b = "".join([t for t in _pretty_typeseq(b)])
            return "%s:%s" % (a,b)

        elif t == CONST_ModuleIdInfo:
            a,b = (self.deref_const(i) for i in v)
            return "%s@%s" % (a,b)

        else:
            return ""



class JavaAttributes(object):

    """ attributes table, as used in class, member, and code
    structures. Requires access to a JavaConstantPool instance for
    many of its methods to work correctly. """


    def __init__(self):
        self.attributes = tuple()



    def unpack(self, unpacker):
        
        """ Unpack an attributes table from an unpacker
        stream. Modifies the structure of this instance. """

        debug("unpacking attributes")

        (count,) = unpacker.unpack(">H")
        items = []

        for i in xrange(0, count):
            debug("unpacking attribute %i of %i" % (i+1, count))

            (name, size) = unpacker.unpack(">HI")

            debug("attribute #%s, %i bytes" % (name, size))
            data = unpacker.read(size)

            items.append( (name, data) )

        self.attributes = tuple(items)



    def get_attributes_as_map(self, cpool):
        cval = cpool.deref_const
        pairs = ((cval(i),v) for (i,v) in self.attributes)
        return dict(pairs)



    def get_attribute(self, name, cpool):

        return self.get_attributes_as_map(cpool).get(name)



class JavaClassInfo(JavaAttributes):

    """ Information from a disassembled Java class file. """

    def __init__(self):
        JavaAttributes.__init__(self)

        self.cpool = JavaConstantPool()

        self.magic = JAVA_CLASS_MAGIC
        self.version = (0, 0)
        self.access_flags = 0
        self.this_ref = 0
        self.super_ref = 0
        self.interfaces = tuple()
        self.fields = tuple()
        self.methods = tuple()



    def deref_const(self, index):
        return self.cpool.deref_const(index)



    def get_attribute(self, name):
        return super(JavaClassInfo, self).get_attribute(name, self.cpool)



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

        self.cpool.unpack(unpacker)
        
        (a, b, c) = unpacker.unpack(">HHH")
        self.access_flags = a
        self.this_ref = b
        self.super_ref = c

        debug("unpacking interfaces")
        (count,) = unpacker.unpack(">H")
        self.interfaces = unpacker.unpack(">%iH" % count)
        
        debug("unpacking fields")
        self.fields = _unpack_objs(unpacker, JavaMemberInfo,
                                   self.cpool, is_method=False)
        
        debug("unpacking methods")
        self.methods = _unpack_objs(unpacker, JavaMemberInfo,
                                    self.cpool, is_method=True)

        JavaAttributes.unpack(self, unpacker)



    def get_field_by_name(self, name):
        for f in self.fields:
            if f.get_name() == name:
                return f
        return None



    def _get_methods_by_name_gen(self, name):
        return (m for m in self.methods if m.get_name() == name)



    def get_methods_by_name(self, name):
        return tuple(self._get_methods_by_name_gen(name))



    def get_method(self, name, arg_types=()):

        """ returns the method matching the name and having argument
        type descriptors matching those in arg_types. This does not
        return any bridge methods. """

        for m in self._get_methods_by_name_gen(name):
            if ((not m.is_bridge) and
                m.get_arg_type_descriptors() == arg_types):
                return m
        return None



    def _get_method_bridges_gen(self, name, arg_types=()):
        for m in self._get_methods_by_name_gen(name):
            if (m.is_bridge and
                m.get_arg_type_descriptors() == arg_types):
                yield m



    def get_method_bridges(self, name, arg_types=()):
        
        """ returns a tuple of bridge methods found that adapt the
        return types of a named method and having argument type
        descriptors matching those in arg_types. """
        
        # I am note entirely certain if a class will generate more
        # than one synthetic bridge method to adapt the return type. I
        # know it will generate one at least if someone subclasses and
        # overrides the method to return a more specific type. If
        # someone were to then subclass again with an even MORE
        # specific type, I am not sure if only one bridge would be
        # generated (adapting to the first super's type) or two
        # (adapting to the first super's type, and another to the
        # original type). I will need to research such insane
        # conditions.

        return tuple(self._get_method_bridges_gen(name, arg_types))



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
        buff = self.get_attribute("SourceFile")
        if buff is None:
            return 0

        (r,) = _unpack(">H", buff)
        return r



    def get_sourcefile(self):
        sfref = self.get_sourcefile_ref()
        if sfref:
            return self.deref_const(sfref)
        else:
            return None



    def get_source_debug_extension(self):
        buff = self.get_attribute("SourceDebugExtension")
        return (buff and str(buff)) or None



    def get_innerclasses(self):
        buff = self.get_attribute("InnerClasses")
        if buff is None:
            return None
        
        up = Unpacker(buff)
        objs = _unpack_objs(up, JavaInnerClassInfo, self.cpool)
        up.close()



    def get_signature(self):
        buff = self.get_attribute("Signature")
        if buff is None:
            return None

        # type index
        (ti,) = _unpack(">H", buff)

        return self.deref_const(ti)



    def get_enclosingmethod(self):
        buff = self.get_attribute("EnclosingMethod")

        # TODO:
        # Running across classes with data in this attribute like
        # 00 06 00 00
        # which would be the 6th const for the class name, and the
        # zero-th (INVALID) const for method. Maybe this is static
        # inner classes?

        if buff is None:
            return None

        # class index, method index
        (ci, mi) = _unpack(">HH", buff)

        if ci and mi:
            enc_class = self.deref_const(ci)
            enc_meth,enc_type = self.deref_const(mi)
            return "%s.%s%s" % (enc_class, enc_meth, enc_type)

        elif ci:
            return self.deref_const(ci)

        else:
            return None



    def _pretty_access_flags_gen(self):
        if self.is_public():
            yield "public"
        if self.is_final():
            yield "final"
        if self.is_interface():
            yield "interface"
        if self.is_abstract():
            yield "abstract"
        #if self.is_super():
        #    yield "super"
        if self.is_annotation():
            yield "annotation"
        if self.is_enum():
            yield "enum"



    def pretty_access_flags(self):
        
        """ tuple of the pretty access flag names """

        return tuple(self._pretty_access_flags_gen())



    def pretty_this(self):
        return _pretty_class(self.get_this())



    def pretty_super(self):
        return _pretty_class(self.get_super())



    def pretty_interfaces(self):
        return tuple(_pretty_class(t) for t in self.get_interfaces())

    

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



    def _get_provides(self, private=False):
        me = self.pretty_this()
        yield me

        for field in self.fields:
            if private or field.is_public():
                yield "%s.%s" % (me, field.pretty_identifier())

        for method in self.methods:
            if private or method.is_public():
                yield "%s.%s" % (me, method.pretty_identifier())



    def _get_requires(self):
        provided = set(self._get_provides(private=True))
        cpool = self.cpool

        # loop through the constant pool for API types
        for i,t,v in cpool.constants():
            pv = None

            if t in (CONST_Class, CONST_Fieldref,
                     CONST_Methodref, CONST_InterfaceMethodref):

                pv = cpool.pretty_deref_const(i)

                if pv[0] == "[":
                    # sometimes when calling operations on an array
                    # the type embeded in the cpool will be the array
                    # type, not just the class type. Let's only gather
                    # the types themselves and ignore the fact that
                    # the class really wanted an array of them.  In
                    # the event that this was a method or field on the
                    # array, we'll throw away that as well, and just
                    # emit the type contained in the array.
                    t,b = _next_argsig(buffer(pv))
                    if t[1] == "L":
                        pv = _pretty_type(t[1:])
                    else:
                        pv = None

                if pv and (pv not in provided):
                    yield pv



    def get_provides(self, ignored=[]):
        from dirutils import fnmatches
        d = set(self._get_provides())
        if ignored:
            d = filter(lambda n: not fnmatches(n, *ignored), d)
        return d



    def get_requires(self, ignored=[]):
        from dirutils import fnmatches
        d = set(self._get_requires())
        if ignored:
            d = filter(lambda n: not fnmatches(n, *ignored), d)
        return d



class JavaMemberInfo(JavaAttributes):

    """ A field or method of a java class """


    def __init__(self, cpool, is_method=False):
        JavaAttributes.__init__(self)

        self.cpool = cpool
        self.access_flags = 0
        self.name_ref = 0
        self.descriptor_ref = 0
        self.is_method = is_method



    def deref_const(self, index):
        return self.cpool.deref_const(index)



    def get_attribute(self, name):
        return super(JavaMemberInfo, self).get_attribute(name, self.cpool)



    def get_signature(self):
        buff = self.get_attribute("Signature")
        if buff is None:
            return None

        # type index
        (ti,) = _unpack(">H", buff)

        return self.deref_const(ti)



    def get_module(self):
        buff = self.get_attribute("Module")
        if buff is None:
            return None

        (ti,) = _unpack(">H", buff)

        return self.deref_const(ti)



    def unpack(self, unpacker):

        debug("unpacking member info")

        (a, b, c) = unpacker.unpack(">HHH")

        self.access_flags = a
        self.name_ref = b
        self.descriptor_ref = c

        JavaAttributes.unpack(self, unpacker)



    def get_name(self):
        return self.deref_const(self.name_ref)



    def get_descriptor(self):
        return self.deref_const(self.descriptor_ref)



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



    def is_module(self):
        return self.access_flags & ACC_MODULE



    def is_deprecated(self):
        return bool(self.get_attribute("Deprecated"))



    def get_code(self):
        buff = self.get_attribute("Code")
        if buff is None:
            return None

        up = Unpacker(buff)

        code = JavaCodeInfo(self.cpool)
        code.unpack(up)

        up.close()

        return code



    def get_exceptions(self):

        """ a tuple class names for the exception types this method
        may raise, or None if this is not a method"""

        buff = self.get_attribute("Exceptions")
        if buff is None:
            return ()

        up = Unpacker(buff)
        excps = _unpack_array(up, ">H")
        up.close()

        return tuple([self.deref_const(e[0]) for e in excps])



    def get_constantvalue(self):

        """ the constant pool index for this field, or None if this is
        not a contant field"""

        buff = self.get_attribute("ConstantValue")
        if buff is None:
            return None

        (cval_ref,) = _unpack(">H", buff)
        return cval_ref



    def deref_constantvalue(self):

        """ the value in the constant pool at the get_constantvalue()
        index """

        index = self.get_constantvalue()
        if index is None:
            return None
        else:
            return self.deref_const(index)



    def get_type_descriptor(self):

        """ the type descriptor for a field, or the return type
        descriptor for a method. Type descriptors are shorthand
        identifiers for the builtin java types. """
        
        return _typeseq(self.get_descriptor())[-1]



    def get_arg_type_descriptors(self):

        """ The parameter type descriptor list for a method, or None
        for a field.  Type descriptors are shorthand identifiers for
        the builtin java types."""

        if not self.is_method:
            return tuple()

        tp = _typeseq(self.get_descriptor())
        tp = _typeseq(tp[0][1:-1])

        return tp



    def pretty_type(self):

        """ The pretty version of get_type_descriptor. """

        return _pretty_type(self.get_type_descriptor())



    def pretty_arg_types(self):

        """ The pretty version of get_arg_type_descriptors. Returns
        () for non-methods """

        if not self.is_method:
            return tuple()

        types = self.get_arg_type_descriptors()
        return tuple(_pretty_type(t) for t in types)



    def pretty_descriptor(self):
        
        """ assemble a long member name from access flags, type,
        argument types, exceptions as applicable """
        
        f = " ".join(self.pretty_access_flags())
        p = self.pretty_type()
        n = self.get_name()
        a = ",".join(self.pretty_arg_types())
        t = ",".join(self.pretty_exceptions())
        
        if n == "<init>":
            # rename this method to match the class name
            #n = self.cpool.get_this()
            #if "/" in n:
            #    n = n[n.rfind("/")+1:]

            # we pretend that there's no return type, even though it's
            # V for constructors
            p = None

        if a:
            # stick the name and args together so there's no space
            n = "%s(%s)" % (n, a)

        if t:
            # assemble any throws as necessary
            t = "throws "+t

        x = [z for z in (f,p,n,t) if z]
        return " ".join(x)



    def _pretty_access_flags_gen(self, all=False):

        if self.is_public():
            yield "public"
        if self.is_private():
            yield "private"
        if self.is_protected():
            yield "protected"
        if self.is_static():
            yield "static"
        if self.is_final():
            yield "final"
        if self.is_strict():
            yield "strict"
        if self.is_native():
            yield "native"
        if self.is_abstract():
            yield "abstract"
        if self.is_enum():
            yield "enum"
        if self.is_module():
            yield "module"

        if all and self.is_synthetic():
            yield "synthetic"

        if self.is_method:
            if self.is_synchronized():
                yield "synchronized"
                
            if all and self.is_bridge():
                yield "bridge"
            if all and self.is_varargs():
                yield "varargs"

        else:
            if self.is_transient():
                yield "transient"
            if self.is_volatile():
                yield "volatile"



    def pretty_access_flags(self, all=False, forclass=True):

        """ tuple of the keywords determined from the access flags"""

        return tuple(self._pretty_access_flags_gen(all))



    def pretty_exceptions(self):

        """ sequence of pretty names for get_exceptions() """

        return tuple(_pretty_class(e) for e in self.get_exceptions())



    def get_identifier(self):

        """  For methods this  is the  return type,  the name  and the
        (non-pretty) argument descriptor. For  fields it is simply the
        name.

        The return-type of methods is attached to the identifier when
        it is a bridge method, which can technically allow two methods
        with the same name and argument type list, but with different
        return type."""

        id = self.get_name()

        if self.is_method:
            args = ",".join(self.get_arg_type_descriptors())
            if self.is_bridge():
                id = "%s(%s):%s" % (id, args, self.get_descriptor())
            else:
                id = "%s(%s)" % (id, args)

        return id



    def pretty_identifier(self):
        id = self.get_name()
        if self.is_method:
            args = ",".join(self.pretty_arg_types())
            id = "%s(%s)" % (id, args)

        return "%s:%s" % (id, self.pretty_type())



class JavaCodeInfo(JavaAttributes):

    """ The 'Code' attribue of a method member of a java class """


    def __init__(self, cpool):
        JavaAttributes.__init__(self)

        self.cpool = cpool
        self.max_stack = 0
        self.max_locals = 0
        self.code = None
        self.exceptions = tuple()



    def deref_const(self, index):
        return self.cpool.deref_const(index)



    def get_attribute(self, name):
        return super(JavaCodeInfo, self).get_attribute(name, self.cpool)



    def unpack(self, unpacker):

        """ unpacks a code block from a buffer. Updates the internal
        structure of this instance """

        debug("unpacking code info")

        (a, b, c) = unpacker.unpack(">HHI")
        
        self.max_stack = a
        self.max_locals = b
        self.code = unpacker.read(c)

        self.exceptions = _unpack_objs(unpacker, JavaExceptionInfo, self)

        JavaAttributes.unpack(self, unpacker)

    

    def get_linenumbertable(self):

        """  a sequence of (code_offset, line_number) pairs """

        buff = self.get_attribute("LineNumberTable")
        if buff is None:
            return None

        up = Unpacker(buff)
        ret = _unpack_array(up, ">HH")
        up.close()

        return ret



    def get_relativelinenumbertable(self):

        """ a sequence of (code_offset, line_number) pairs. Similar to
        the get_linenumbertable method, but the line numbers start at
        0 (they are relative to the method, not to the class file) """
        
        lnt = self.get_linenumbertable()
        if lnt:
            lineoff = lnt[0][1]
            return [(o,l-lineoff) for (o,l) in lnt]
        else:
            return tuple()
        


    def get_localvariabletable(self):
        
        """ a sequence of (code_offset, length, name_index,
        desc_index, index) tuples """

        buff = self.get_attribute("LocalVariableTable")
        if buff is None:
            return None

        up = Unpacker(buff)
        ret = _unpack_array(up, ">HHHHH")
        up.close()
        return ret
    


    def get_localvariabletypetable(self):
        
        """ a sequence of (code_offset, length, name_index,
        signature_index, index) tuples """

        buff = self.get_attribute("LocalVariableTypeTable")
        if buff is None:
            return None

        up = Unpacker(buff)
        ret = _unpack_array(up, ">HHHHH")
        up.close()
        return ret


    def get_line_for_offset(self, code_offset):

        """ returns the line number given a code offset """

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
        
        """ disassembles the underlying bytecode instructions and
        generates a sequence of (offset, code, args) tuples"""

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

        """ unpacks an exception handler entry in an exception
        table. Updates the internal structure of this instance """

        debug("unpacking Exception info")

        (a, b, c, d) = unpacker.unpack(">HHHH")

        self.start_pc = a
        self.end_pc = b
        self.handler_pc = c
        self.catch_type_ref = d


    def get_catch_type(self):
        if self.catch_type_ref:
            return self.cpool.deref_const(self.catch_type_ref)
        else:
            return None


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


    def __str__(self):
        return "(%s)" % ",".join(self.__cmp_tuple())



class JavaInnerClassInfo(object):

    """ Information about an inner class """    

    def __init__(self, cpool):
        self.cpool = cpool

        self.inner_info_ref = 0
        self.outer_info_ref = 0
        self.name_ref = 0
        self.access_flags = 0


    def unpack(self, unpacker):

        debug("unpacking JavaInnerClass")

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
    up = Unpacker(data)
    ret = up.unpack(fmt)
    up.close()
    return ret



def _unpack_objs(unpacker, atype, *params, **kwds):

    """ The common pattern is to have a count and then that many times
    of an object. The unpacker class doesn't presume to know the count
    type, so this function gets the count first"""
    
    (count,) = unpacker.unpack(">H")
    return unpacker.unpack_objects(count, atype, *params, **kwds)



def _unpack_array(unpacker, fmt):

    """ The common pattern is to have a count and then that many times
    of an object. The unpacker class doesn't presume to know the count
    type, so this function gets the count first"""
    
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
                      CONST_InterfaceMethodref, CONST_NameAndType,
                      CONST_ModuleIdInfo):
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
    elif typecode == CONST_ModuleIdInfo:
        typestr = "ModuleIdInfo"
        val = "#%i@#%i" % val
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
        raise Unimplemented("_next_argsig is %r in %s" % (c, str(buff)))



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
    elif tc == "T":
        return "generic " + s[1:]
    elif tc == "L":
        return _pretty_class(s[1:-1])
    elif tc == "[":
        return "%s[]" % _pretty_type(s[1:])
    else:
        raise Unimplemented("unknown type, %r" % tc)
        


def _pretty_class(s):
    
    # well that's easy.
    return s.replace("/", ".")



def _clean_array_const(s):
    t,b = _next_argsig(buffer(s))
    return (t,str(b))


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



_struct_cache = {}

def compile_struct(fmt):

    """ returns a Struct instance compiled from fmt. If fmt has
    already been compiled, it will return the previously compiled
    Struct instance. """

    sfmt = _struct_cache.get(fmt, None)
    if not sfmt:
        debug("compiling struct format %r" % fmt)
        sfmt = Struct(fmt)
        _struct_cache[fmt] = sfmt
    return sfmt



class Unpacker(object):


    """ Wraps a stream (or creates a stream for a string or buffer)
    and advances along it while unpacking structures from it. """


    def __init__(self, data):
        from StringIO import StringIO
        
        if isinstance(data, str) or isinstance(data, buffer):
            self.stream = StringIO(data)
        elif hasattr(data, "read"):
            self.stream = data
        else:
            raise TypeError("Unpacker requires a string, buffer,"
                            " or object with a read method")


    def unpack(self, fmt):
        sfmt = compile_struct(fmt)
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

        """ unpacks fmt count times and returns the tuple of results
        """

        return tuple(self.unpack_array_gen(count, fmt))
    

    def unpack_objects_gen(self, count, atype, *params, **kwds):
        for i in xrange(0, count):
            o = atype(*params, **kwds)
            o.unpack(self)
            yield o


    def unpack_objects(self, count, atype, *params, **kwds):

        """ instanciates count atypes by calling it with the given params and
        keywords, then calls the instance's unpack method, passing
        this unpacker as the only argument. """

        return tuple(self.unpack_objects_gen(count, atype, *params, **kwds))


    def read(self, i):
        buff = self.stream.read(i)
        if len(buff) < i:
            raise UnpackException(None, i, len(buff))
        return buff


    def close(self):
        if hasattr(self.stream, "close"):
            self.stream.close()
        del self.stream


#
# Functions for dealing with buffers and files



def is_class(data):

    """ checks that the data (which is a string, buffer, or a stream
    supporting the read method) has the magic numbers indicating it is
    a Java class file. Returns False if the magic numbers do not
    match, or for any errors. """

    try:
        unpacker = Unpacker(data)
        magic = unpacker.unpack(">BBBB")
        unpacker.close()
        return magic == JAVA_CLASS_MAGIC

    except:
        return False



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
    already. In this case, pass those magic bytes as a str or tuple
    and the unpacker will not attempt to read them again.  """

    unpacker = Unpacker(data)

    magic = magic or unpacker.unpack(">BBBB")
    if magic != JAVA_CLASS_MAGIC:
        return None
    
    o = JavaClassInfo()
    o.unpack(unpacker, magic=magic)

    unpacker.close()

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
