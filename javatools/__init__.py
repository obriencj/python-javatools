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
Simple Java Classfile unpacking module. Can be made to act an
awful lot like the javap utility included with most Java SDKs.

Most of the information used to write this was gathered from the
following web pages

References
----------
* http://docs.oracle.com/javase/specs/jvms/se7/html/jvms-4.html
* http://java.sun.com/docs/books/jvms/second_edition/html/VMSpecTOC.doc.html
* http://en.wikipedia.org/wiki/Class_(file_format)

:author: Christopher O'Brien  <obriencj@gmail.com>
:license: LGPL
"""  # noqa


from functools import partial
from six.moves import range

from .dirutils import fnmatches
from .opcodes import disassemble
from .pack import compile_struct, unpack, UnpackException

try:
    buffer
except NameError:
    buffer = memoryview


__all__ = (
    "JavaClassInfo", "JavaConstantPool", "JavaMemberInfo",
    "JavaCodeInfo", "JavaExceptionInfo", "JavaInnerClassInfo",
    "JavaAnnotation",
    "NoPoolException", "Unimplemented", "ClassUnpackException",
    "platform_from_version",
    "is_class", "is_class_file",
    "unpack_class", "unpack_classfile",
    "CONST_Utf8", "CONST_Integer", "CONST_Float",
    "CONST_Long", "CONST_Double", "CONST_Class",
    "CONST_String", "CONST_Fieldref", "CONST_Methodref",
    "CONST_InterfaceMethodref", "CONST_NameAndType",
    "CONST_ModuleId", "CONST_MethodHandle",
    "CONST_MethodType", "CONST_InvokeDynamic",
    "CONST_Module", "CONST_Package",
    "ACC_PUBLIC", "ACC_PRIVATE", "ACC_PROTECTED",
    "ACC_STATIC", "ACC_FINAL", "ACC_SYNCHRONIZED",
    "ACC_SUPER", "ACC_VOLATILE", "ACC_BRIDGE",
    "ACC_TRANSIENT", "ACC_VARARGS", "ACC_NATIVE",
    "ACC_INTERFACE", "ACC_ABSTRACT", "ACC_STRICT",
    "ACC_SYNTHETIC", "ACC_ANNOTATION", "ACC_ENUM",
    "ACC_MODULE",
)


# the four bytes at the start of every class file
JAVA_CLASS_MAGIC = (0xCA, 0xFE, 0xBA, 0xBE)


_BUFFERING = 2 ** 14


# The constant pool types
# pylint: disable=C0103
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
CONST_ModuleId = 13  # Removed? Maybe OpenJDK only?
CONST_MethodHandle = 15  # TODO
CONST_MethodType = 16  # TODO
CONST_InvokeDynamic = 18  # TODO
CONST_Module = 19
CONST_Package = 20


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


# commonly re-occurring struct formats
_B = compile_struct(">B")
_BBBB = compile_struct(">BBBB")
_BH = compile_struct(">BH")
_H = compile_struct(">H")
_HH = compile_struct(">HH")
_HHH = compile_struct(">HHH")
_HHHH = compile_struct(">HHHH")
_HHHHH = compile_struct(">HHHHH")
_HI = compile_struct(">HI")
_HHI = compile_struct(">HHI")


class NoPoolException(Exception):
    """
    raised by methods that need a JavaConstantPool, but aren't
    provided one on the owning instance
    """

    pass


class Unimplemented(Exception):
    """
    raised when something unexpected happens, which usually indicates
    part of the classfile specification that wasn't implemented in
    this module yet
    """

    pass


class ClassUnpackException(Exception):
    """
    raised when a class couldn't be unpacked
    """

    pass


class JavaConstantPool(object):
    """
    A constants pool

    reference: http://docs.oracle.com/javase/specs/jvms/se7/html/jvms-4.html#jvms-4.4
    """  # noqa

    def __init__(self):
        self.consts = tuple()


    def __eq__(self, other):
        return (isinstance(other, JavaConstantPool) and
                (self.consts == other.consts))


    def __ne__(self, other):
        return not self.__eq__(other)


    def unpack(self, unpacker):
        """
        Unpacks the constant pool from an unpacker stream
        """

        (count, ) = unpacker.unpack_struct(_H)

        # first item is never present in the actual data buffer, but
        # the count number acts like it would be.
        items = [(None, None), ]
        count -= 1

        # Long and Double const types will "consume" an item count,
        # but not data
        hackpass = False

        for _i in range(0, count):

            if hackpass:
                # previous item was a long or double
                hackpass = False
                items.append((None, None))

            else:
                item = _unpack_const_item(unpacker)
                items.append(item)

                # if this item was a long or double, skip the next
                # counter.
                if item[0] in (CONST_Long, CONST_Double):
                    hackpass = True

        self.consts = items


    def get_const(self, index):
        """
        returns the type and value of the constant at index
        """

        return self.consts[index]


    def deref_const(self, index):
        """
        returns the dereferenced value from the const pool. For simple
        types, this will be a single value indicating the constant.
        For more complex types, such as fieldref, methodref, etc, this
        will return a tuple.
        """

        if not index:
            raise IndexError("Requested const 0")

        t, v = self.consts[index]

        if t in (CONST_Utf8, CONST_Integer, CONST_Float,
                 CONST_Long, CONST_Double):
            return v

        elif t in (CONST_Class, CONST_String, CONST_MethodType):
            return self.deref_const(v)

        elif t in (CONST_Fieldref, CONST_Methodref,
                   CONST_InterfaceMethodref, CONST_NameAndType,
                   CONST_ModuleId, CONST_Module, CONST_Package):
            return tuple(self.deref_const(i) for i in v)

        elif t == CONST_InvokeDynamic:
            # TODO: v[0] needs to come from the bootstrap methods table
            return (v[0], self.deref_const(v[1]))

        else:
            raise Unimplemented("Unknown constant pool type %r" % t)


    def constants(self):
        """
        sequence of tuples (index, type, dereferenced value) of the
        constant pool entries.
        """

        for i in range(1, len(self.consts)):
            t, _v = self.consts[i]
            if t:
                yield (i, t, self.deref_const(i))


    def pretty_constants(self):
        """
        the sequence of tuples (index, pretty type, value) of the constant
        pool entries.
        """

        for i in range(1, len(self.consts)):
            t, v = self.pretty_const(i)
            if t:
                yield (i, t, v)


    def pretty_const(self, index):
        """
        a tuple of the pretty type and val, or (None, None) for invalid
        indexes (such as the second part of a long or double value)
        """

        t, v = self.consts[index]
        if not t:
            return None, None
        else:
            return _pretty_const_type_val(t, v)


    def pretty_deref_const(self, index):
        """
        A string representation of the end-value of a constant.  This will
        deref the constant index, and if it is a compound type, will
        continue dereferencing until it can compose the full value
        (eg: a CONST_Methodref will be composed of its class, name,
        and value derefenced constants)
        """

        t, v = self.consts[index]

        if t == CONST_String:
            result = self.deref_const(v)

        elif t in (CONST_Utf8,
                   CONST_Integer, CONST_Float,
                   CONST_Long, CONST_Double):
            result = v

        elif t == CONST_Class:
            result = _pretty_class(self.deref_const(v))

        elif t == CONST_Fieldref:
            cn = self.deref_const(v[0])
            cn = _pretty_class(cn)

            n, t = self.deref_const(v[1])

            result = "%s.%s:%s" % (cn, n, _pretty_type(t))

        elif t in (CONST_Methodref,
                   CONST_InterfaceMethodref):

            cn = self.deref_const(v[0])
            cn = _pretty_class(cn)

            n, t = self.deref_const(v[1])

            args, ret = tuple(_pretty_typeseq(t))

            result = "%s.%s%s:%s" % (cn, n, args, ret)

        elif t == CONST_NameAndType:
            a, b = (self.deref_const(i) for i in v)
            b = "".join(_pretty_typeseq(b))
            result = "%s:%s" % (a, b)

        elif t == CONST_ModuleId:
            a, b = (self.deref_const(i) for i in v)
            result = "%s@%s" % (a, b)

        elif t == CONST_InvokeDynamic:
            # TODO: v[0] needs to come from the bootstrap methods table
            result = "InvokeDynamic %r %r" % (v[0], self.deref_const(v[1]))

        elif t == CONST_Module:
            result = "Module %s" % self.deref_cons(v[0])

        elif t == CONST_Package:
            result = "Package %s" % self.deref_cons(v[0])

        elif not t:
            # the skipped-type, meaning the prior index was a
            # two-slotter.
            result = ""

        else:
            raise Unimplemented("No pretty for const type %r" % t)

        return result


class JavaAttributes(dict):
    """
    attributes table, as used in class, member, and code
    structures. Requires access to a JavaConstantPool instance for
    many of its methods to work correctly.
    """

    def __init__(self, cpool):
        dict.__init__(self)
        self.cpool = cpool


    def unpack(self, unpacker):
        """
        Unpack an attributes table from an unpacker stream.  Modifies the
        structure of this instance.
        """

        # bound method for dereferencing constants
        cval = self.cpool.deref_const

        (count,) = unpacker.unpack_struct(_H)
        for _i in range(0, count):
            (name, size) = unpacker.unpack_struct(_HI)
            self[cval(name)] = unpacker.read(size)


class JavaClassInfo(object):
    """
    Information from a disassembled Java class file.

    reference: http://docs.oracle.com/javase/specs/jvms/se7/html/jvms-4.html
    """

    def __init__(self):
        self.cpool = JavaConstantPool()
        self.attribs = JavaAttributes(self.cpool)

        self.magic = JAVA_CLASS_MAGIC
        self.version = (0, 0)
        self.access_flags = 0
        self.this_ref = 0
        self.super_ref = 0
        self.interfaces = tuple()
        self.fields = tuple()
        self.methods = tuple()
        self.annotations = None
        self.invisible_annotations = None

        self._provides = None
        self._provides_private = None
        self._requires = None


    def deref_const(self, index):
        """
        dereference a value from the parent constant pool
        """

        return self.cpool.deref_const(index)


    def get_attribute(self, name):
        """
        get an attribute buffer by name
        """

        return self.attribs.get(name)


    def unpack(self, unpacker, magic=None):
        """
        Unpacks a Java class from an unpacker stream. Updates the
        structure of this instance.

        If the unpacker has already had the magic header read off of
        it, the read value may be passed via the optional magic
        parameter and it will not attempt to read the value again.
        """

        # only unpack the magic bytes if it wasn't specified
        magic = magic or unpacker.unpack_struct(_BBBB)

        if isinstance(magic, (str, buffer)):
            magic = tuple(ord(m) for m in magic)
        else:
            magic = tuple(magic)

        if magic != JAVA_CLASS_MAGIC:
            raise ClassUnpackException("Not a Java class file")

        self.magic = magic

        # unpack (minor, major), store as (major, minor)
        self.version = unpacker.unpack_struct(_HH)[::-1]

        # unpack constant pool
        self.cpool.unpack(unpacker)

        (a, b, c) = unpacker.unpack_struct(_HHH)
        self.access_flags = a
        self.this_ref = b
        self.super_ref = c

        # unpack interfaces
        (count,) = unpacker.unpack_struct(_H)
        self.interfaces = unpacker.unpack(">%iH" % count)

        uobjs = unpacker.unpack_objects

        # unpack fields
        self.fields = tuple(uobjs(JavaMemberInfo,
                                  self.cpool, is_method=False))

        # unpack methods
        self.methods = tuple(uobjs(JavaMemberInfo,
                                   self.cpool, is_method=True))

        # unpack attributes
        self.attribs.unpack(unpacker)


    def get_field_by_name(self, name):
        """
        the field member matching name, or None if no such field is found
        """

        for f in self.fields:
            if f.get_name() == name:
                return f
        return None


    def get_methods_by_name(self, name):
        """
        generator of methods matching name. This will include any bridges
        present.
        """

        return (m for m in self.methods if m.get_name() == name)


    def get_method(self, name, arg_types=()):
        """
        searches for the method matching the name and having argument type
        descriptors matching those in arg_types.

        Parameters
        ==========
        arg_types : sequence of strings
          each string is a parameter type, in the non-pretty format.

        Returns
        =======
        method : `JavaMemberInfo` or `None`
          the single matching, non-bridging method of matching name
          and parameter types.
        """

        # ensure any lists or iterables are converted to tuple for
        # comparison against get_arg_type_descriptors()
        arg_types = tuple(arg_types)

        for m in self.get_methods_by_name(name):
            if (((not m.is_bridge()) and
                 m.get_arg_type_descriptors() == arg_types)):
                return m
        return None


    def get_method_bridges(self, name, arg_types=()):
        """
        generator of bridge methods found that adapt the return types of a
        named method and having argument type descriptors matching
        those in arg_types.
        """

        for m in self.get_methods_by_name(name):
            if ((m.is_bridge() and
                 m.get_arg_type_descriptors() == arg_types)):
                yield m


    def get_version(self):
        """
        the (major, minor) version of Java required by this Java class
        """

        return self.version


    def get_platform(self):
        """
        The platform as a string, derived from the major and minor version
        number
        """

        return platform_from_version(*self.version)


    def is_public(self):
        """
        is this class public
        """

        return self.access_flags & ACC_PUBLIC


    def is_final(self):
        """
        is this class final
        """

        return self.access_flags & ACC_FINAL


    def is_super(self):
        """
        class has the Super flag set.

        This flag is used by the JVM to differentiate the behavior in
        the method resolution order of the class.
        """

        return self.access_flags & ACC_SUPER


    def is_interface(self):
        """
        is this an interface
        """

        return self.access_flags & ACC_INTERFACE


    def is_abstract(self):
        """
        is this an abstract class
        """

        return self.access_flags & ACC_ABSTRACT


    def is_annotation(self):
        """
        is this an annotation class
        """

        return self.access_flags & ACC_ANNOTATION


    def is_enum(self):
        """
        is this an enum class
        """

        return self.access_flags & ACC_ENUM


    def get_this(self):
        """
        the name of this class
        """

        return self.deref_const(self.this_ref)


    def is_deprecated(self):
        """
        is this class deprecated

        reference: http://docs.oracle.com/javase/specs/jvms/se7/html/jvms-4.html#jvms-4.7.15
        """  # noqa

        return bool(self.get_attribute("Deprecated"))


    def get_super(self):
        """
        get the parent class that this extends
        """

        return self.deref_const(self.super_ref) if self.super_ref else ""


    def get_interfaces(self):
        """
        tuple of interfaces that this class implements
        """

        return tuple(self.deref_const(i) for i in self.interfaces)


    def _get_annotations(self, python_attr_name, java_attr_name):

        annos = getattr(self, python_attr_name)

        if annos is None:
            buff = self.get_attribute(java_attr_name)
            if buff is None:
                annos = tuple()

            else:
                with unpack(buff) as up:
                    annos = up.unpack_objects(JavaAnnotation, self.cpool)
                    annos = tuple(annos)

            setattr(self, python_attr_name, annos)

        return annos


    def get_annotations(self):
        """
        The RuntimeVisibleAnnotations attribute. A tuple of JavaAnnotation
        instances

        reference: http://docs.oracle.com/javase/specs/jvms/se7/html/jvms-4.html#jvms-4.7.16
        """  # noqa

        return self._get_annotations("annotations",
                                     "RuntimeVisibleAnnotations")


    def get_invisible_annotations(self):
        """
        The RuntimeInvisibleAnnotations attribute. A tuple of
        JavaAnnotation instances

        reference: http://docs.oracle.com/javase/specs/jvms/se7/html/jvms-4.html#jvms-4.7.17
        """  # noqa

        return self._get_annotations("invisible_annotations",
                                     "RuntimeInvisibleAnnotations")


    def get_sourcefile(self):
        """
        the name of thie file this class was compiled from, or None if not
        indicated

        reference: http://docs.oracle.com/javase/specs/jvms/se7/html/jvms-4.html#jvms-4.7.10
        """  # noqa

        buff = self.get_attribute("SourceFile")
        if buff is None:
            return None

        with unpack(buff) as up:
            (ref,) = up.unpack_struct(_H)

        return self.deref_const(ref)


    def get_source_debug_extension(self):
        """
        reference:
        http://docs.oracle.com/javase/specs/jvms/se7/html/jvms-4.html#jvms-4.7.11
        """  # noqa

        buff = self.get_attribute("SourceDebugExtension")
        return (buff and str(buff)) or None


    def get_innerclasses(self):
        """
        sequence of JavaInnerClassInfo instances describing the inner
        classes of this class definition

        reference: http://docs.oracle.com/javase/specs/jvms/se7/html/jvms-4.html#jvms-4.7.6
        """  # noqa

        buff = self.get_attribute("InnerClasses")
        if buff is None:
            return tuple()

        with unpack(buff) as up:
            return tuple(up.unpack_objects(JavaInnerClassInfo, self.cpool))


    def get_signature(self):
        """
        the generics class signature

        reference: http://docs.oracle.com/javase/specs/jvms/se7/html/jvms-4.html#jvms-4.7.9
        """  # noqa

        buff = self.get_attribute("Signature")
        if buff is None:
            return None

        with unpack(buff) as up:
            (ref,) = up.unpack_struct(_H)

        return self.deref_const(ref)


    def pretty_signature(self):
        """
        pretty version of the signature
        """

        return pretty_generic(self.get_signature())


    def get_enclosingmethod(self):
        """
        the class.method or class (if the definition is not from within a
        method) that encloses the definition of this class. Returns
        None if this was not an inner class.

        reference: http://docs.oracle.com/javase/specs/jvms/se7/html/jvms-4.html#jvms-4.7.7
        """  # noqa

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
        with unpack(buff) as up:
            ci, mi = up.unpack_struct(_HH)

        result = None

        if ci and mi:
            enc_class = self.deref_const(ci)
            enc_meth, enc_type = self.deref_const(mi)
            result = "%s.%s%s" % (enc_class, enc_meth, enc_type)

        elif ci:
            result = self.deref_const(ci)

        return result


    def _pretty_access_flags_gen(self):
        """
        generator of the pretty access flags
        """

        if self.is_public():
            yield "public"
        if self.is_final():
            yield "final"
        if self.is_abstract():
            yield "abstract"
        if self.is_interface():
            if self.is_annotation():
                yield "@interface"
            else:
                yield "interface"
        if self.is_enum():
            yield "enum"


    def pretty_access_flags(self):
        """
        generator of the pretty access flag names
        """

        return self._pretty_access_flags_gen()


    def pretty_this(self):
        """
        the pretty version of this class name
        """

        return _pretty_class(self.get_this())


    def pretty_super(self):
        """
        the pretty version of the parent class name
        """

        return _pretty_class(self.get_super())


    def pretty_interfaces(self):
        """
        the pretty versions of any interfaces this class implements
        """

        return (_pretty_class(t) for t in self.get_interfaces())


    def pretty_descriptor(self):
        """
        get the class or interface name, its accessor flags, its parent
        class, and any interfaces it implements
        """

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
        """
        iterator of provided classes, fields, methods
        """

        # TODO I probably need to add inner classes here

        me = self.pretty_this()
        yield me

        for field in self.fields:
            if private or field.is_public():
                yield "%s.%s" % (me, field.pretty_identifier())

        for method in self.methods:
            if private or method.is_public():
                yield "%s.%s" % (me, method.pretty_identifier())


    def _get_requires(self):
        """
        iterator of required classes, fields, methods, determined my
        mining the constant pool for such types
        """

        provided = set(self.get_provides(private=True))
        cpool = self.cpool

        # loop through the constant pool for API types
        for i, t, _v in cpool.constants():

            if t in (CONST_Class, CONST_Fieldref,
                     CONST_Methodref, CONST_InterfaceMethodref):

                # convert this away from unicode so we can
                pv = str(cpool.pretty_deref_const(i))

                if pv[0] == "[":
                    # sometimes when calling operations on an array
                    # the type embeded in the cpool will be the array
                    # type, not just the class type. Let's only gather
                    # the types themselves and ignore the fact that
                    # the class really wanted an array of them.  In
                    # the event that this was a method or field on the
                    # array, we'll throw away that as well, and just
                    # emit the type contained in the array.
                    t = _typeseq(pv)
                    if t[1] == "L":
                        pv = _pretty_type(t[1:])
                    else:
                        pv = None

                if pv and (pv not in provided):
                    yield pv


    def get_provides(self, ignored=tuple(), private=False):
        """
        The provided API, including the class itself, its fields, and its
        methods.
        """

        if private:
            if self._provides_private is None:
                self._provides_private = set(self._get_provides(True))
            provides = self._provides_private
        else:
            if self._provides is None:
                self._provides = set(self._get_provides(False))
            provides = self._provides

        return [prov for prov in provides if not fnmatches(prov, *ignored)]


    def get_requires(self, ignored=tuple()):
        """
        The required API, including all external classes, fields, and
        methods that this class references
        """

        if self._requires is None:
            self._requires = set(self._get_requires())

        requires = self._requires
        return [req for req in requires if not fnmatches(req, *ignored)]


class JavaMemberInfo(object):
    """
    A field or method of a java class
    """

    def __init__(self, cpool, is_method=False):
        self.cpool = cpool
        self.attribs = JavaAttributes(cpool)
        self.access_flags = 0
        self.name_ref = 0
        self.descriptor_ref = 0
        self.is_method = is_method
        self.annotations = None
        self.invisible_annotations = None
        self.parameter_annotations = None
        self.invisible_parameter_annotations = None


    def deref_const(self, index):
        """
        Dereference a constant in the parent constant pool
        """

        return self.cpool.deref_const(index)


    def get_attribute(self, name):
        """
        Get an attribute buffer by name
        """

        return self.attribs.get(name)


    def get_signature(self):
        """
        the Signature attribute
        """

        buff = self.get_attribute("Signature")
        if buff is None:
            return None

        # type index
        with unpack(buff) as up:
            (ti,) = up.unpack_struct(_H)

        return self.deref_const(ti)


    def pretty_signature(self):
        """
        pretty version of the signature
        """

        return pretty_generic(self.get_signature())


    def get_module(self):
        """
        the Module attribute
        """

        buff = self.get_attribute("Module")
        if buff is None:
            return None

        with unpack(buff) as up:
            (ti,) = up.unpack_struct(_H)

        return self.deref_const(ti)


    def unpack(self, unpacker):
        """
        unpack the contents of this instance from the values in unpacker
        """

        (a, b, c) = unpacker.unpack_struct(_HHH)

        self.access_flags = a
        self.name_ref = b
        self.descriptor_ref = c
        self.attribs.unpack(unpacker)


    def get_name(self):
        """
        the name of this member
        """

        return self.deref_const(self.name_ref)


    def get_descriptor(self):
        """
        the descriptor of this member
        """

        return self.deref_const(self.descriptor_ref)


    def is_public(self):
        """
        is this member public
        """

        return self.access_flags & ACC_PUBLIC


    def is_private(self):
        """
        is this member private
        """

        return self.access_flags & ACC_PRIVATE


    def is_protected(self):
        """
        is this member protected
        """

        return self.access_flags & ACC_PROTECTED


    def is_static(self):
        """
        is this member static
        """

        return self.access_flags & ACC_STATIC


    def is_final(self):
        """
        is this member final
        """

        return self.access_flags & ACC_FINAL


    def is_synchronized(self):
        """
        is this member synchronized
        """

        return self.access_flags & ACC_SYNCHRONIZED


    def is_native(self):
        """
        is this member native
        """

        return self.access_flags & ACC_NATIVE


    def is_abstract(self):
        """
        is this member abstract
        """

        return self.access_flags & ACC_ABSTRACT


    def is_strict(self):
        """
        is this member strict
        """

        return self.access_flags & ACC_STRICT


    def is_volatile(self):
        """
        is this member volatile
        """

        return self.access_flags & ACC_VOLATILE


    def is_transient(self):
        """
        is this member transient
        """

        return self.access_flags & ACC_TRANSIENT


    def is_bridge(self):
        """
        is this method a bridge to another method
        """

        return self.access_flags & ACC_BRIDGE


    def is_varargs(self):
        """
        is this a varargs method
        """

        return self.access_flags & ACC_VARARGS


    def is_synthetic(self):
        """
        is this a synthetic method

        reference: http://docs.oracle.com/javase/specs/jvms/se7/html/jvms-4.html#jvms-4.7.8
        """  # noqa

        return ((self.access_flags & ACC_SYNTHETIC) or
                bool(self.get_attribute("Synthetic")))


    def is_enum(self):
        """
        it this member an enum
        """

        return self.access_flags & ACC_ENUM


    def is_module(self):
        """
        is this a module member
        """

        return self.access_flags & ACC_MODULE


    def is_deprecated(self):
        """
        is this member deprecated

        reference: http://docs.oracle.com/javase/specs/jvms/se5.0/html/ClassFile.doc.html#78232
        """  # noqa

        return bool(self.get_attribute("Deprecated"))


    def _get_annotations(self, python_attr_name, java_attr_name,
                         for_params=False):

        annos = getattr(self, python_attr_name)

        if annos is None:
            buff = self.get_attribute(java_attr_name)
            if buff is None:
                annos = tuple()

            else:
                with unpack(buff) as up:
                    unp = partial(up.unpack_objects,
                                  JavaAnnotation, self.cpool)

                    if for_params:
                        (param_count, ) = up.unpack_struct(_B)
                        annos = (tuple(unp()) for _i in range(param_count))
                    else:
                        annos = unp()
                    annos = tuple(annos)

            setattr(self, python_attr_name, annos)

        return annos


    def get_annotations(self):
        """
        The RuntimeVisibleAnnotations attribute. A tuple of JavaAnnotation
        instances

        reference: http://docs.oracle.com/javase/specs/jvms/se7/html/jvms-4.html#jvms-4.7.16
        """  # noqa

        return self._get_annotations("annotations",
                                     "RuntimeVisibleAnnotations")


    def get_invisible_annotations(self):
        """
        The RuntimeInvisibleAnnotations attribute. A tuple of
        JavaAnnotation instances

        reference: http://docs.oracle.com/javase/specs/jvms/se7/html/jvms-4.html#jvms-4.7.17
        """  # noqa

        return self._get_annotations("invisible_annotations",
                                     "RuntimeInvisibleAnnotations")


    def get_parameter_annotations(self):
        """
        The RuntimeVisibleParameterAnnotations attribute.  Contains a
        tuple of JavaAnnotation instances for each param.

        reference: http://docs.oracle.com/javase/specs/jvms/se7/html/jvms-4.html#jvms-4.7.18
        """  # noqa
        return self._get_annotations("parameter_annotations",
                                     "RuntimeVisibleParameterAnnotations",
                                     for_params=True)


    def get_invisible_parameter_annotations(self):
        """
        The RuntimeInvisibleParameterAnnotations attribute.  Contains a
        tuple of JavaAnnotation instances for each param.

        reference: http://docs.oracle.com/javase/specs/jvms/se7/html/jvms-4.html#jvms-4.7.19
        """  # noqa
        return self._get_annotations("invisible_parameter_annotations",
                                     "RuntimeInvisibleParameterAnnotations",
                                     for_params=True)


    def get_annotationdefault(self):
        """
        The AnnotationDefault attribute, only present upon fields in an
        annotaion.

        reference: http://docs.oracle.com/javase/specs/jvms/se7/html/jvms-4.html#jvms-4.7.20
        """  # noqa

        buff = self.get_attribute("AnnotationDefault")
        if buff is None:
            return None

        with unpack(buff) as up:
            (ti, ) = up.unpack_struct(_H)

        return ti


    def deref_annotationdefault(self):
        """
        dereferences the AnnotationDefault attribute
        """

        index = self.get_annotationdefault()
        if index is None:
            return None
        else:
            return self.deref_const(index)


    def get_code(self):
        """
        the JavaCodeInfo of this member if it is a non-abstract method,
        None otherwise

        reference: http://docs.oracle.com/javase/specs/jvms/se7/html/jvms-4.html#jvms-4.7.3
        """  # noqa

        buff = self.get_attribute("Code")
        if buff is None:
            return None

        with unpack(buff) as up:
            code = JavaCodeInfo(self.cpool)
            code.unpack(up)

        return code


    def get_exceptions(self):
        """
        a tuple of class names for the exception types this method may
        raise, or None if this is not a method

        reference: http://docs.oracle.com/javase/specs/jvms/se7/html/jvms-4.html#jvms-4.7.5
        """  # noqa

        buff = self.get_attribute("Exceptions")
        if buff is None:
            return ()

        with unpack(buff) as up:
            return tuple(self.deref_const(e[0]) for e
                         in up.unpack_struct_array(_H))


    def get_constantvalue(self):
        """
        the constant pool index for this field, or None if this is not a
        contant field

        reference: http://docs.oracle.com/javase/specs/jvms/se7/html/jvms-4.html#jvms-4.7.2
        """  # noqa

        buff = self.get_attribute("ConstantValue")
        if buff is None:
            return None

        with unpack(buff) as up:
            (cval_ref, ) = up.unpack_struct(_H)

        return cval_ref


    def deref_constantvalue(self):
        """
        the value in the constant pool at the get_constantvalue() index
        """

        index = self.get_constantvalue()
        if index is None:
            return None
        else:
            return self.deref_const(index)


    def get_type_descriptor(self):
        """
        the type descriptor for a field, or the return type descriptor for
        a method. Type descriptors are shorthand identifiers for the
        builtin java types.
        """

        return _typeseq(self.get_descriptor())[-1]


    def get_arg_type_descriptors(self):
        """
        The parameter type descriptor list for a method, or None for a
        field.  Type descriptors are shorthand identifiers for the
        builtin java types.
        """

        if not self.is_method:
            return tuple()

        desc = self.get_descriptor()

        tp = _typeseq(desc)
        tp = _typeseq(tp[0][1:-1])

        return tp


    def pretty_type(self):
        """
        The pretty version of get_type_descriptor.
        """

        return _pretty_type(self.get_type_descriptor())


    def pretty_arg_types(self):
        """
        Sequence of pretty argument types.
        """

        if self.is_method:
            types = self.get_arg_type_descriptors()
            return (_pretty_type(t) for t in types)
        else:
            return tuple()


    def pretty_descriptor(self):
        """
        assemble a long member name from access flags, type, argument
        types, exceptions as applicable
        """

        f = " ".join(self.pretty_access_flags())
        p = self.pretty_type()
        n = self.get_name()
        t = ",".join(self.pretty_exceptions())

        if n == "<init>":
            # we pretend that there's no return type, even though it's
            # V for constructors
            p = None

        if self.is_method:
            # stick the name and args together so there's no space
            n = "%s(%s)" % (n, ",".join(self.pretty_arg_types()))

        if t:
            # assemble any throws as necessary
            t = "throws " + t

        return " ".join(z for z in (f, p, n, t) if z)


    def _pretty_access_flags_gen(self, showall=False):

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

        if showall and self.is_synthetic():
            yield "synthetic"

        if self.is_method:
            if self.is_synchronized():
                yield "synchronized"

            if showall and self.is_bridge():
                yield "bridge"
            if showall and self.is_varargs():
                yield "varargs"

        else:
            if self.is_transient():
                yield "transient"
            if self.is_volatile():
                yield "volatile"


    def pretty_access_flags(self, showall=False):
        """
        generator of the keywords determined from the access flags
        """

        return self._pretty_access_flags_gen(showall)


    def pretty_exceptions(self):
        """
        sequence of pretty names for get_exceptions()
        """

        return (_pretty_class(e) for e in self.get_exceptions())


    def get_identifier(self):
        """
        For methods this is the return type, the name and the (non-pretty)
        argument descriptor. For fields it is simply the name.

        The return-type of methods is attached to the identifier when
        it is a bridge method, which can technically allow two methods
        with the same name and argument type list, but with different
        return type.
        """

        ident = self.get_name()

        if self.is_method:
            args = ",".join(self.get_arg_type_descriptors())
            if self.is_bridge():
                ident = "%s(%s):%s" % (ident, args, self.get_descriptor())
            else:
                ident = "%s(%s)" % (ident, args)

        return ident


    def pretty_identifier(self):
        """
        The pretty version of get_identifier
        """

        ident = self.get_name()
        if self.is_method:
            args = ",".join(self.pretty_arg_types())
            ident = "%s(%s)" % (ident, args)

        return "%s:%s" % (ident, self.pretty_type())


class JavaCodeInfo(object):
    """
    The 'Code' attribue of a method member of a java class

    reference: http://docs.oracle.com/javase/specs/jvms/se7/html/jvms-4.html#jvms-4.7.3
    """  # noqa

    def __init__(self, cpool):
        self.cpool = cpool
        self.attribs = JavaAttributes(cpool)
        self.max_stack = 0
        self.max_locals = 0
        self.code = None
        self.exceptions = tuple()

        # cache of disassembled code
        self._dis_code = None

        # cache of linenumbertable
        self._lnt = None


    def deref_const(self, index):
        """
        dereference a constant by index from the parent constant pool
        """

        return self.cpool.deref_const(index)


    def get_attribute(self, name):
        """
        get an attribute buffer by name
        """

        return self.attribs.get(name)


    def unpack(self, unpacker):
        """
        unpacks a code block from a buffer. Updates the internal structure
        of this instance
        """

        (a, b, c) = unpacker.unpack_struct(_HHI)

        self.max_stack = a
        self.max_locals = b
        self.code = unpacker.read(c)

        uobjs = unpacker.unpack_objects
        self.exceptions = tuple(uobjs(JavaExceptionInfo, self))

        self.attribs.unpack(unpacker)


    def get_linenumbertable(self):
        """
        a sequence of (code_offset, line_number) pairs.

        reference: http://docs.oracle.com/javase/specs/jvms/se7/html/jvms-4.html#jvms-4.7.12
        """  # noqa

        lnt = self._lnt
        if lnt is None:
            buff = self.get_attribute("LineNumberTable")
            if buff is None:
                lnt = tuple()
            else:
                with unpack(buff) as up:
                    lnt = tuple(up.unpack_struct_array(_HH))
            self._lnt = lnt
        return lnt


    def get_relativelinenumbertable(self):
        """
        a sequence of (code_offset, line_number) pairs. Similar to the
        get_linenumbertable method, but the line numbers start at 0
        (they are relative to the method, not to the class file)
        """

        lnt = self.get_linenumbertable()
        if lnt:
            lineoff = lnt[0][1]
            return tuple((o, l - lineoff) for (o, l) in lnt)
        else:
            return tuple()


    def get_localvariabletable(self):
        """
        a sequence of (code_offset, length, name_index, desc_index, index)
        tuples

        reference: http://docs.oracle.com/javase/specs/jvms/se7/html/jvms-4.html#jvms-4.7.13
        """  # noqa

        buff = self.get_attribute("LocalVariableTable")
        if buff is None:
            return tuple()

        with unpack(buff) as up:
            return tuple(up.unpack_struct_array(_HHHHH))


    def get_localvariabletypetable(self):
        """
        a sequence of (code_offset, length, name_index, signature_index,
        index) tuples

        reference: http://docs.oracle.com/javase/specs/jvms/se7/html/jvms-4.html#jvms-4.7.14
        """  # noqa

        buff = self.get_attribute("LocalVariableTypeTable")
        if buff is None:
            return tuple()

        with unpack(buff) as up:
            return tuple(up.unpack_struct_array(_HHHHH))


    def get_line_for_offset(self, code_offset):
        """
        returns the line number given a code offset
        """

        prev_line = 0

        for (offset, line) in self.get_linenumbertable():
            if offset < code_offset:
                prev_line = line
            elif offset == code_offset:
                return line
            else:
                return prev_line

        return prev_line


    def iter_code_by_lines(self):
        """
        ((abs_line, rel_line, [(offset, code, args), ...]),
         ...)
        """

        lnt = self.get_linenumbertable()
        if not lnt:
            yield (1, 1, self.disassemble())
            return

        lnt_offset = lnt[0][1]

        cur_line = None
        current = None

        for codelet in self.disassemble():
            abs_line = self.get_line_for_offset(codelet[0])

            if cur_line == abs_line:
                current.append(codelet)

            else:
                if cur_line is not None:
                    yield (cur_line, cur_line - lnt_offset, current)
                cur_line = abs_line
                current = [codelet]

        if current:
            yield (cur_line, cur_line - lnt_offset, current)


    def disassemble(self):
        """
        disassembles the underlying bytecode instructions and generates a
        sequence of (offset, code, args) tuples
        """

        dis = self._dis_code
        if dis is None:
            dis = tuple(disassemble(self.code))
            self._dis_code = dis

        return dis


class JavaExceptionInfo(object):
    """
    Information about an exception handler entry in an exception table
    """

    def __init__(self, code):
        self.code = code
        self.cpool = code.cpool

        self.start_pc = 0
        self.end_pc = 0
        self.handler_pc = 0
        self.catch_type_ref = 0


    def unpack(self, unpacker):
        """
        unpacks an exception handler entry in an exception table. Updates
        the internal structure of this instance
        """

        (a, b, c, d) = unpacker.unpack_struct(_HHHH)

        self.start_pc = a
        self.end_pc = b
        self.handler_pc = c
        self.catch_type_ref = d


    def get_catch_type(self):
        """
        dereferences the catch_type_ref to its class name, or None if the
        catch type is unspecified
        """

        if self.catch_type_ref:
            return self.cpool.deref_const(self.catch_type_ref)
        else:
            return None


    def pretty_catch_type(self):
        """
        pretty version of `get_catch_type()`

        If the catch type isn't specified, returns "any". Otherwise
        prefixes the pretty class name with the text "Class ". This is
        done to emulate the javap output for exceptions caught in a
        body of code.
        """

        ct = self.get_catch_type()
        if ct:
            return "Class " + _pretty_class(ct)
        else:
            return "any"


    def info(self):
        """
        tuple of the start_pc, end_pc, handler_pc and catch_type_ref
        """

        return (self.start_pc, self.end_pc,
                self.handler_pc, self.get_catch_type())


    def __eq__(self, other):
        return (isinstance(other, JavaExceptionInfo) and
                (self.info() == other.info()))


    def __ne__(self, other):
        return not self.__eq__(other)


    def __str__(self):
        return "(%s)" % ",".join(self.info())


class JavaInnerClassInfo(object):
    """
    Information about an inner class

    reference: http://docs.oracle.com/javase/specs/jvms/se7/html/jvms-4.html#jvms-4.7.6
    """  # noqa

    def __init__(self, cpool):
        self.cpool = cpool

        self.inner_info_ref = 0
        self.outer_info_ref = 0
        self.name_ref = 0
        self.access_flags = 0


    def unpack(self, unpacker):
        """
        unpack this instance with data from unpacker
        """

        (a, b, c, d) = unpacker.unpack_struct(_HHHH)

        self.inner_info_ref = a
        self.outer_info_ref = b
        self.name_ref = c
        self.access_flags = d


    def get_name(self):
        """
        the name of this inner-class
        """

        return self.cpool.deref_const(self.name_ref)


class JavaAnnotation(dict):
    """
    Java Annotations info

    reference: http://docs.oracle.com/javase/specs/jvms/se7/html/jvms-4.html#jvms-4.7.16
    """  # noqa

    def __init__(self, cpool):
        dict.__init__(self)
        self.cpool = cpool
        self.type_ref = 0


    def unpack(self, unpacker):
        self.type_ref, count = unpacker.unpack_struct(_HH)

        for _i in range(0, count):
            key_ref, = unpacker.unpack_struct(_H)
            val = _unpack_annotation_val(unpacker, self.cpool)

            key = self.cpool.deref_const(key_ref)
            self[key] = val


    def pretty_type(self):
        return _pretty_type(self.cpool.deref_const(self.type_ref))


    def pretty_elements(self):
        result = list()

        for key, val in self.items():
            val = _pretty_annotation_val(val, self.cpool)
            result.append("%s=%s" % (key, val))

        return result


    def pretty_annotation(self):
        typename = self.pretty_type()
        elements = self.pretty_elements()
        return "%s(%s)" % (typename, ", ".join(elements))


    def __eq__(self, other):
        if not isinstance(other, JavaAnnotation):
            return False

        # if we have a different type name, not equal
        left = self.cpool.deref_const(self.type_ref)
        right = other.cpool.deref_const(other.type_ref)
        if left != right:
            return False

        # if we have differing sets of keys, not equal
        if self.keys() != other.keys():
            return False

        # for each of the key/val pairs, check equality
        for key, lval in self.items():
            rval = other[key]
            if not _annotation_val_eq(lval[0], lval[1], self.cpool,
                                      rval[0], rval[1], other.cpool):
                return False
        return True


    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return '@' + self.pretty_annotation()


def _annotation_val_eq(left_tag, left_data, left_cpool,
                       right_tag, right_data, right_cpool):

    if left_tag != right_tag:
        return False

    lconst = left_cpool.deref_const
    rconst = right_cpool.deref_const

    if left_tag in 'BCDFIJSZs':
        return lconst(left_data) == rconst(right_data)

    elif left_tag == 'e':
        return ((lconst(left_data[0]) == rconst(right_data[0])) and
                (lconst(left_data[1]) == rconst(right_data[1])))

    elif left_tag == 'c':
        return lconst(left_data) == rconst(right_data)

    elif left_tag == '@':
        return left_data == right_data

    elif left_tag == '[':
        if len(left_data) != len(right_data):
            return False

        for index in range(0, len(left_data)):
            ld = left_data[index]
            rd = right_data[index]
            if not _annotation_val_eq(ld[0], ld[1], left_cpool,
                                      rd[0], rd[1], right_cpool):
                return False
        return True


def _unpack_annotation_val(unpacker, cpool):
    """
    tag, data tuple of an annotation
    """

    tag, = unpacker.unpack_struct(_B)
    tag = chr(tag)

    if tag in 'BCDFIJSZs':
        data, = unpacker.unpack_struct(_H)

    elif tag == 'e':
        data = unpacker.unpack_struct(_HH)

    elif tag == 'c':
        data, = unpacker.unpack_struct(_H)

    elif tag == '@':
        data = JavaAnnotation(cpool)
        data.unpack(unpacker)

    elif tag == '[':
        data = list()
        count, = unpacker.unpack_struct(_H)
        for _i in range(0, count):
            data.append(_unpack_annotation_val(unpacker, cpool))

    else:
        raise Unimplemented("Unknown tag {}".format(tag))

    return tag, data


def _pretty_annotation_val(val, cpool):
    """
    a pretty display of a tag and data pair annotation value
    """

    tag, data = val

    if tag in 'BCDFIJSZs':
        data = "%s#%i" % (tag, data)

    elif tag == 'e':
        data = "e#%i.#%i" % data

    elif tag == 'c':
        data = "c#%i" % data

    elif tag == '@':
        data = "@" + data.pretty_annotation()

    elif tag == '[':
        combine = list()
        for val in data:
            combine.append(_pretty_annotation_val(val, cpool))
        data = "[%s]" % ", ".join(combine)

    return data


# -----
# Utility functions for turning major/minor versions into JVM releases
# Each entry is a tuple of minimum version and maxiumum version,
# inclusive, and the string of the platform version.


_platforms = (
    ((45, 0), (45, 3), "1.0.2"),
    ((45, 4), (45, 65535), "1.1"),
    ((46, 0), (46, 65535), "1.2"),
    ((47, 0), (47, 65535), "1.3"),
    ((48, 0), (48, 65535), "1.4"),
    ((49, 0), (49, 65535), "1.5"),
    ((50, 0), (50, 65535), "1.6"),
    ((51, 0), (51, 65535), "1.7"),
    ((52, 0), (52, 65535), "1.8"), )


def platform_from_version(major, minor):
    """
    returns the minimum platform version that can load the given class
    version indicated by major.minor or None if no known platforms
    match the given version
    """

    v = (major, minor)
    for low, high, name in _platforms:
        if low <= v <= high:
            return name
    return None


# -----
# Utility functions for the constants pool


def _unpack_const_item(unpacker):
    """
    unpack a constant pool item, which will consist of a type byte
    (see the CONST_ values in this module) and a value of the
    appropriate type
    """

    (typecode,) = unpacker.unpack_struct(_B)

    if typecode == CONST_Utf8:
        (slen,) = unpacker.unpack_struct(_H)
        val = unpacker.read(slen)
        try:
            val = val.decode("utf8")
        except UnicodeDecodeError:
            # easiest hack to handle java's modified utf-8 encoding
            val = val.replace(b"\xC0\x80", b"\x00").decode("utf8")

    elif typecode == CONST_Integer:
        (val,) = unpacker.unpack(">i")

    elif typecode == CONST_Float:
        (val,) = unpacker.unpack(">f")

    elif typecode == CONST_Long:
        (val,) = unpacker.unpack(">q")

    elif typecode == CONST_Double:
        (val,) = unpacker.unpack(">d")

    elif typecode in (CONST_Class, CONST_String, CONST_MethodType,
                      CONST_Module, CONST_Package):
        (val,) = unpacker.unpack_struct(_H)

    elif typecode in (CONST_Fieldref, CONST_Methodref,
                      CONST_InterfaceMethodref, CONST_NameAndType,
                      CONST_ModuleId, CONST_InvokeDynamic):
        val = unpacker.unpack_struct(_HH)

    elif typecode == CONST_MethodHandle:
        val = unpacker.unpack_struct(_BH)

    elif typecode == CONST_MethodType:
        val = unpacker.unpack_struct(_H)

    else:
        raise Unimplemented("unknown constant type %r" % typecode)

    return typecode, val


def _pretty_const_type_val(typecode, val):
    """
    given a typecode and a value, returns the appropriate pretty
    version of that value (not the dereferenced data)
    """

    if typecode == CONST_Utf8:
        typestr = "Utf8"  # formerly Asciz, which was considered Java bug
        if not isinstance(val, str):  # Py2, val is 'unicode'
            val = repr(val)[2:-1]  # trim off the surrounding u"" (HACK)
        else:
            val = repr(val)[1:-1]  # trim off the surrounding "" (HACK)
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
    elif typecode == CONST_ModuleId:
        typestr = "ModuleId"
        val = "#%i@#%i" % val
    elif typecode == CONST_MethodHandle:
        typestr = "MethodHandle"
        val = repr(val)
    elif typecode == CONST_MethodType:
        typestr = "MethodType"
        val = repr(val)
    elif typecode == CONST_InvokeDynamic:
        typestr = "InvokeDynamic"
        val = repr(val)
    elif typecode == CONST_Module:
        typestr = "Module"
    elif typecode == CONST_Package:
        typestr = "Package"
    else:
        raise Unimplemented("unknown constant type %r" % typecode)

    return typestr, val


# -----
# Utility functions for dealing with exploding internal type
# signatures into sequences, and converting type signatures into
# "pretty" strings


def pretty_generic(signature):
    """
    Pretty version of the given generics signature
    """

    # TODO: this format is annoying in so many ways.

    return signature


def _next_argsig(s):
    """
    given a string, find the next complete argument signature and
    return it and a new string advanced past that point
    """

    c = s[0]

    if c in "BCDFIJSVZ":
        result = (c, s[1:])

    elif c == "[":
        d, s = _next_argsig(s[1:])
        result = (c + d, s)

    elif c == "L":
        i = s.find(';') + 1
        result = (s[:i], s[i:])

    elif c == "(":
        i = s.find(')') + 1
        result = (s[:i], s[i:])

    else:
        raise Unimplemented("_next_argsig is %r in %r" % (c, s))

    return result


def _typeseq_iter(s):
    """
    iterate through all of the type signatures in a sequence
    """

    original = s
    try:
        s = str(s)
        while s:
            t, s = _next_argsig(s)
            yield t

    except Unimplemented:
        raise Unimplemented("Unknown type signature in %r" % original)


def _typeseq(type_s):
    """
    tuple version of _typeseq_iter
    """

    return tuple(_typeseq_iter(type_s))


def _pretty_typeseq(type_s):
    """
    iterator of pretty versions of _typeseq_iter
    """

    return (_pretty_type(t) for t in _typeseq(type_s))


def _pretty_type(s, offset=0):
    # pylint: disable=R0911, R0912
    # too many returns, too many branches. Not converting this to a
    # dict lookup. Waiving instead.

    """
    returns the pretty version of a type code
    """

    tc = s[offset]

    if tc == "V":
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
        return _pretty_class(s[offset + 1:-1])

    elif tc == "[":
        return "%s[]" % _pretty_type(s, offset + 1)

    elif tc == "(":
        return "(%s)" % ",".join(_pretty_typeseq(s[offset + 1:-1]))

    elif tc == "T":
        return "generic " + s[offset + 1:]

    else:
        raise Unimplemented("unknown type, %r" % tc)


def _pretty_class(s):
    """
    convert the internal class name representation into what users
    expect to see. Currently that just means swapping '/' for '.'
    """

    # well that's easy.
    return s.replace("/", ".")


# -----
# Functions for dealing with buffers and files


def is_class(data):
    """
    checks that the data (which is a string, buffer, or a stream
    supporting the read method) has the magic numbers indicating it is
    a Java class file. Returns False if the magic numbers do not
    match, or for any errors.
    """

    try:
        with unpack(data) as up:
            magic = up.unpack_struct(_BBBB)

        return magic == JAVA_CLASS_MAGIC

    except UnpackException:
        return False


def is_class_file(filename):
    """
    checks whether the given file is a Java class file, by opening it
    and checking for the magic header
    """

    with open(filename, "rb") as fd:
        c = fd.read(len(JAVA_CLASS_MAGIC))
        if isinstance(c, str):      # Python 2
            c = map(ord, c)
        return tuple(c) == JAVA_CLASS_MAGIC


def unpack_class(data, magic=None):
    """
    unpacks a Java class from data, which can be a string, a buffer,
    or a stream supporting the read method. Returns a populated
    JavaClassInfo instance.

    If data is a stream which has already been confirmed to be a java
    class, it may have had the first four bytes read from it already.
    In this case, pass those magic bytes as a str or tuple and the
    unpacker will not attempt to read them again.

    Raises a ClassUnpackException or an UnpackException if the class
    data is malformed. Raises Unimplemented if a feature is discovered
    which isn't understood by javatools yet.
    """

    with unpack(data) as up:
        magic = magic or up.unpack_struct(_BBBB)
        if magic != JAVA_CLASS_MAGIC:
            raise ClassUnpackException("Not a Java class file")

        o = JavaClassInfo()
        o.unpack(up, magic=magic)

    return o


def unpack_classfile(filename):
    """
    returns a newly allocated JavaClassInfo object populated with the
    data unpacked from the specified file. Raises an UnpackException
    if the class data is malformed
    """

    with open(filename, "rb", _BUFFERING) as fd:
        return unpack_class(fd.read())


#
# The end.
