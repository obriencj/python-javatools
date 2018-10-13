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
unit tests for python-javatools

author: Christopher O'Brien  <obriencj@gmail.com>
license: LGPL v.3
"""


from unittest import TestCase

import javatools as jt
import javatools.opcodes as op
import pkg_resources


def get_data_fn(which):
    which = "data/%s" % which
    fn = pkg_resources.resource_filename(__name__, which)
    return fn


def get_class_fn(which):
    return get_data_fn(which + ".class")


def load(which):
    fn = get_class_fn(which)
    return jt.unpack_classfile(fn)


class Sample1Tests(TestCase):

    def test_is_class_file(self):
        fn = get_class_fn("Sample1")
        self.assertTrue(jt.is_class_file(fn))

    def test_is_class(self):
        fn = get_class_fn("Sample1")
        with open(fn, "rb") as f:
            data = f.read()
        self.assertTrue(jt.is_class(data))

    def test_classinfo(self):
        ci = load("Sample1")

        self.assertEqual(type(ci), jt.JavaClassInfo)

        self.assertEqual(ci.get_this(), "Sample1")
        self.assertEqual(ci.pretty_this(), "Sample1")

        self.assertEqual(ci.get_sourcefile(), "Sample1.java")

        self.assertTrue(ci.is_public())
        self.assertTrue(ci.is_super())

        self.assertFalse(ci.is_final())
        self.assertFalse(ci.is_interface())
        self.assertFalse(ci.is_abstract())
        self.assertFalse(ci.is_annotation())
        self.assertFalse(ci.is_enum())
        self.assertFalse(ci.is_deprecated())

        self.assertEqual(ci.get_super(), "java/lang/Object")
        self.assertEqual(ci.pretty_super(), "java.lang.Object")

        # not a generic class, no signature
        self.assertEqual(ci.get_signature(), None)
        self.assertEqual(ci.pretty_signature(), None)

        self.assertEqual(ci.pretty_descriptor(),
                         "public class Sample1 extends java.lang.Object")

        self.assertEqual(ci.get_interfaces(), tuple())
        self.assertEqual(tuple(ci.pretty_interfaces()), tuple())

        # not an inner class, so no enclosing method
        self.assertEqual(ci.get_enclosingmethod(), None)

        self.assertEqual(ci.get_innerclasses(), tuple())
        self.assertEqual(ci.get_annotations(), tuple())
        self.assertEqual(ci.get_invisible_annotations(), tuple())


    def test_const_pool(self):
        ci = load("Sample1")

        exp = ( (0, (None, None)),
                (1, (jt.CONST_String, 24)),
                (2, (jt.CONST_Methodref, (6, 25))),
                (3, (jt.CONST_Methodref, (7, 26))),
                (4, (jt.CONST_Fieldref, (6, 27))),
                (5, (jt.CONST_Fieldref, (6, 28))),
                (6, (jt.CONST_Class, 29)),
                (7, (jt.CONST_Class, 30)),
                (8, (jt.CONST_Utf8, 'DEFAULT_NAME')),
                (9, (jt.CONST_Utf8, 'Ljava/lang/String;')),
                (10, (jt.CONST_Utf8, u'ConstantValue')),
                (11, (jt.CONST_Utf8, u'name')),
                (12, (jt.CONST_Utf8, u'recent_name')),
                (13, (jt.CONST_Utf8, u'<init>')),
                (14, (jt.CONST_Utf8, u'()V')),
                (15, (jt.CONST_Utf8, u'Code')),
                (16, (jt.CONST_Utf8, u'LineNumberTable')),
                (17, (jt.CONST_Utf8, u'(Ljava/lang/String;)V')),
                (18, (jt.CONST_Utf8, u'getName')),
                (19, (jt.CONST_Utf8, u'()Ljava/lang/String;')),
                (20, (jt.CONST_Utf8, u'getRecentName')),
                (21, (jt.CONST_Utf8, u'<clinit>')),
                (22, (jt.CONST_Utf8, u'SourceFile')),
                (23, (jt.CONST_Utf8, u'Sample1.java')),
                (24, (jt.CONST_Utf8, u'Daphne')),
                (25, (jt.CONST_NameAndType, (13, 17))),
                (26, (jt.CONST_NameAndType, (13, 14))),
                (27, (jt.CONST_NameAndType, (11, 9))),
                (28, (jt.CONST_NameAndType, (12, 9))),
                (29, (jt.CONST_Utf8, u'Sample1')),
                (30, (jt.CONST_Utf8, u'java/lang/Object')) )

        col = tuple(enumerate(ci.cpool.consts))

        self.assertEqual(col, exp)

        # requesting
        x = lambda: ci.cpool.deref_const(0)
        self.assertRaises(IndexError, x)


    def test_field_name(self):
        ci = load("Sample1")
        fi = ci.get_field_by_name("name")

        self.assertEqual(type(fi), jt.JavaMemberInfo)

        self.assertEqual(fi.get_name(), "name")
        self.assertEqual(fi.get_type_descriptor(),
                         "Ljava/lang/String;")
        self.assertEqual(fi.get_descriptor(),
                         "Ljava/lang/String;")
        self.assertEqual(fi.pretty_type(),
                         "java.lang.String")
        self.assertEqual(fi.pretty_descriptor(),
                         "private java.lang.String name")

        self.assertTrue(fi.is_private())

        self.assertFalse(fi.is_public())
        self.assertFalse(fi.is_protected())
        self.assertFalse(fi.is_static())
        self.assertFalse(fi.is_final())
        self.assertFalse(fi.is_synchronized())
        self.assertFalse(fi.is_native())
        self.assertFalse(fi.is_abstract())
        self.assertFalse(fi.is_strict())
        self.assertFalse(fi.is_volatile())
        self.assertFalse(fi.is_transient())
        self.assertFalse(fi.is_bridge())
        self.assertFalse(fi.is_varargs())
        self.assertFalse(fi.is_synthetic())
        self.assertFalse(fi.is_enum())
        self.assertFalse(fi.is_module())
        self.assertFalse(fi.is_deprecated())
        self.assertFalse(fi.is_method)

        self.assertEqual(fi.deref_constantvalue(), None)


    def test_field_recent_name(self):
        ci = load("Sample1")
        fi = ci.get_field_by_name("recent_name")

        self.assertEqual(type(fi), jt.JavaMemberInfo)

        self.assertEqual(fi.get_name(), "recent_name")
        self.assertEqual(fi.get_type_descriptor(),
                         "Ljava/lang/String;")
        self.assertEqual(fi.get_descriptor(),
                         "Ljava/lang/String;")
        self.assertEqual(fi.pretty_type(),
                         "java.lang.String")
        self.assertEqual(fi.pretty_descriptor(),
                         "protected static java.lang.String recent_name")

        self.assertTrue(fi.is_protected())
        self.assertTrue(fi.is_static())

        self.assertFalse(fi.is_public())
        self.assertFalse(fi.is_private())
        self.assertFalse(fi.is_final())
        self.assertFalse(fi.is_synchronized())
        self.assertFalse(fi.is_native())
        self.assertFalse(fi.is_abstract())
        self.assertFalse(fi.is_strict())
        self.assertFalse(fi.is_volatile())
        self.assertFalse(fi.is_transient())
        self.assertFalse(fi.is_bridge())
        self.assertFalse(fi.is_varargs())
        self.assertFalse(fi.is_synthetic())
        self.assertFalse(fi.is_enum())
        self.assertFalse(fi.is_module())
        self.assertFalse(fi.is_deprecated())
        self.assertFalse(fi.is_method)

        self.assertEqual(fi.deref_constantvalue(), None)


    def test_field_default_name(self):
        ci = load("Sample1")
        fi = ci.get_field_by_name("DEFAULT_NAME")

        self.assertEqual(type(fi), jt.JavaMemberInfo)

        self.assertEqual(fi.get_name(), "DEFAULT_NAME")
        self.assertEqual(fi.get_type_descriptor(),
                         "Ljava/lang/String;")
        self.assertEqual(fi.get_descriptor(),
                         "Ljava/lang/String;")
        self.assertEqual(fi.pretty_type(),
                         "java.lang.String")
        self.assertEqual(fi.pretty_descriptor(),
                         "public static final java.lang.String DEFAULT_NAME")

        self.assertTrue(fi.is_public())
        self.assertTrue(fi.is_static())
        self.assertTrue(fi.is_final())

        self.assertFalse(fi.is_private())
        self.assertFalse(fi.is_protected())
        self.assertFalse(fi.is_synchronized())
        self.assertFalse(fi.is_native())
        self.assertFalse(fi.is_abstract())
        self.assertFalse(fi.is_strict())
        self.assertFalse(fi.is_volatile())
        self.assertFalse(fi.is_transient())
        self.assertFalse(fi.is_bridge())
        self.assertFalse(fi.is_varargs())
        self.assertFalse(fi.is_synthetic())
        self.assertFalse(fi.is_enum())
        self.assertFalse(fi.is_module())
        self.assertFalse(fi.is_deprecated())
        self.assertFalse(fi.is_method)

        self.assertEqual(fi.deref_constantvalue(), "Daphne")


    def test_method_init(self):
        ci = load("Sample1")

        mis = list(ci.get_methods_by_name("<init>"))
        self.assertEqual(len(mis), 2)

        mi0 = ci.get_method("<init>")
        self.assertEqual(type(mi0), jt.JavaMemberInfo)

        mi1 = ci.get_method("<init>", ["Ljava/lang/String;"])
        self.assertEqual(type(mi1), jt.JavaMemberInfo)

        self.assertEqual(mis, [mi0, mi1])

        self.assertEqual(mi0.get_name(), "<init>")
        self.assertEqual(mi0.get_type_descriptor(), "V")
        self.assertEqual(mi0.get_descriptor(), "()V")
        self.assertEqual(mi0.get_identifier(), "<init>()")
        self.assertEqual(mi0.pretty_type(), "void")
        self.assertEqual(mi0.pretty_descriptor(), "public <init>()")
        self.assertEqual(mi0.pretty_identifier(), "<init>():void")

        self.assertTrue(mi0.is_public())
        self.assertTrue(mi0.is_method)

        self.assertFalse(mi0.is_private())
        self.assertFalse(mi0.is_protected())
        self.assertFalse(mi0.is_static())
        self.assertFalse(mi0.is_final())
        self.assertFalse(mi0.is_synchronized())
        self.assertFalse(mi0.is_native())
        self.assertFalse(mi0.is_abstract())
        self.assertFalse(mi0.is_strict())
        self.assertFalse(mi0.is_volatile())
        self.assertFalse(mi0.is_transient())
        self.assertFalse(mi0.is_bridge())
        self.assertFalse(mi0.is_varargs())
        self.assertFalse(mi0.is_synthetic())
        self.assertFalse(mi0.is_enum())
        self.assertFalse(mi0.is_module())
        self.assertFalse(mi0.is_deprecated())

        self.assertEqual(mi1.get_name(), "<init>")
        self.assertEqual(mi1.get_type_descriptor(), "V")
        self.assertEqual(mi1.get_descriptor(),
                         "(Ljava/lang/String;)V")
        self.assertEqual(mi1.get_identifier(),
                         "<init>(Ljava/lang/String;)")
        self.assertEqual(mi1.pretty_type(), "void")
        self.assertEqual(mi1.pretty_descriptor(),
                         "public <init>(java.lang.String)")
        self.assertEqual(mi1.pretty_identifier(),
                         "<init>(java.lang.String):void")

        self.assertTrue(mi1.is_public())
        self.assertTrue(mi1.is_method)

        self.assertFalse(mi1.is_private())
        self.assertFalse(mi1.is_protected())
        self.assertFalse(mi1.is_static())
        self.assertFalse(mi1.is_final())
        self.assertFalse(mi1.is_synchronized())
        self.assertFalse(mi1.is_native())
        self.assertFalse(mi1.is_abstract())
        self.assertFalse(mi1.is_strict())
        self.assertFalse(mi1.is_volatile())
        self.assertFalse(mi1.is_transient())
        self.assertFalse(mi1.is_bridge())
        self.assertFalse(mi1.is_varargs())
        self.assertFalse(mi1.is_synthetic())
        self.assertFalse(mi1.is_enum())
        self.assertFalse(mi1.is_module())
        self.assertFalse(mi1.is_deprecated())


    def test_method_get_name(self):
        ci = load("Sample1")
        mi = ci.get_method("getName")

        self.assertEqual(type(mi), jt.JavaMemberInfo)

        self.assertEqual(mi.get_name(), "getName")
        self.assertEqual(mi.get_type_descriptor(), "Ljava/lang/String;")
        self.assertEqual(mi.get_descriptor(), "()Ljava/lang/String;")
        self.assertEqual(mi.get_identifier(), "getName()")
        self.assertEqual(mi.pretty_type(), "java.lang.String")
        self.assertEqual(mi.pretty_descriptor(),
                         "public java.lang.String getName()")
        self.assertEqual(mi.pretty_identifier(),
                         "getName():java.lang.String")

        self.assertTrue(mi.is_public())
        self.assertTrue(mi.is_method)

        self.assertFalse(mi.is_private())
        self.assertFalse(mi.is_protected())
        self.assertFalse(mi.is_static())
        self.assertFalse(mi.is_final())
        self.assertFalse(mi.is_synchronized())
        self.assertFalse(mi.is_native())
        self.assertFalse(mi.is_abstract())
        self.assertFalse(mi.is_strict())
        self.assertFalse(mi.is_volatile())
        self.assertFalse(mi.is_transient())
        self.assertFalse(mi.is_bridge())
        self.assertFalse(mi.is_varargs())
        self.assertFalse(mi.is_synthetic())
        self.assertFalse(mi.is_enum())
        self.assertFalse(mi.is_module())
        self.assertFalse(mi.is_deprecated())


    def test_method_code_name(self):
        ci = load("Sample1")
        mi = ci.get_method("getName")
        code = mi.get_code()

        self.assertEqual(type(code), jt.JavaCodeInfo)

        lnt = code.get_linenumbertable()
        exp = ((0, 18), )

        self.assertEqual(lnt, exp)

        lnt = code.get_relativelinenumbertable()
        exp = ((0, 0), )

        self.assertEqual(lnt, exp)

        dis = tuple(code.disassemble())

        exp = ((0, op.OP_aload_0, ()),
               (1, op.OP_getfield, (4,)),
               (4, op.OP_areturn, ()))

        self.assertEqual(dis, exp)

        # this is the field loaded via OP_getfield
        self.assertEqual(ci.cpool.pretty_deref_const(4),
                         "Sample1.name:java.lang.String")


    def test_method_get_recent_name(self):
        ci = load("Sample1")
        mi = ci.get_method("getRecentName")

        self.assertEqual(type(mi), jt.JavaMemberInfo)

        self.assertEqual(mi.get_name(), "getRecentName")
        self.assertEqual(mi.get_type_descriptor(), "Ljava/lang/String;")
        self.assertEqual(mi.get_descriptor(), "()Ljava/lang/String;")
        self.assertEqual(mi.get_identifier(), "getRecentName()")
        self.assertEqual(mi.pretty_type(), "java.lang.String")
        self.assertEqual(mi.pretty_descriptor(),
                         "public static java.lang.String getRecentName()")
        self.assertEqual(mi.pretty_identifier(),
                         "getRecentName():java.lang.String")

        self.assertTrue(mi.is_public())
        self.assertTrue(mi.is_static())
        self.assertTrue(mi.is_method)

        self.assertFalse(mi.is_private())
        self.assertFalse(mi.is_protected())
        self.assertFalse(mi.is_final())
        self.assertFalse(mi.is_synchronized())
        self.assertFalse(mi.is_native())
        self.assertFalse(mi.is_abstract())
        self.assertFalse(mi.is_strict())
        self.assertFalse(mi.is_volatile())
        self.assertFalse(mi.is_transient())
        self.assertFalse(mi.is_bridge())
        self.assertFalse(mi.is_varargs())
        self.assertFalse(mi.is_synthetic())
        self.assertFalse(mi.is_enum())
        self.assertFalse(mi.is_module())
        self.assertFalse(mi.is_deprecated())


    def test_method_code_recent_name(self):
        ci = load("Sample1")
        mi = ci.get_method("getRecentName")
        code = mi.get_code()

        self.assertEqual(type(code), jt.JavaCodeInfo)

        lnt = code.get_linenumbertable()
        exp = ((0, 22), )

        self.assertEqual(lnt, exp)

        lnt = code.get_relativelinenumbertable()
        exp = ((0, 0), )

        self.assertEqual(lnt, exp)

        dis = tuple(code.disassemble())

        exp = ((0, op.OP_getstatic, (5,)),
               (3, op.OP_areturn, ()))

        self.assertEqual(dis, exp)

        # this is the static field loaded via OP_getstatic
        self.assertEqual(ci.cpool.pretty_deref_const(5),
                         "Sample1.recent_name:java.lang.String")


class Sample2Test(TestCase):

    def test_interface(self):
        ci = load("Sample2I")

        self.assertEqual(type(ci), jt.JavaClassInfo)

        self.assertEqual(ci.get_this(), "Sample2I")
        self.assertEqual(ci.pretty_this(), "Sample2I")

        self.assertEqual(ci.get_sourcefile(), "Sample2I.java")

        self.assertTrue(ci.is_public())
        self.assertTrue(ci.is_interface())
        self.assertTrue(ci.is_abstract())

        self.assertFalse(ci.is_final())
        self.assertFalse(ci.is_super())
        self.assertFalse(ci.is_annotation())
        self.assertFalse(ci.is_enum())
        self.assertFalse(ci.is_deprecated())

        self.assertEqual(ci.get_super(), "java/lang/Object")
        self.assertEqual(ci.pretty_super(), "java.lang.Object")

        # not a generic class, no signature
        self.assertEqual(ci.get_signature(), None)
        self.assertEqual(ci.pretty_signature(), None)

        self.assertEqual(ci.pretty_descriptor(),
                         "public abstract interface Sample2I"
                         " extends java.lang.Object")

        self.assertEqual(ci.get_interfaces(), tuple())
        self.assertEqual(tuple(ci.pretty_interfaces()), tuple())

        # not an inner class, so no enclosing method
        self.assertEqual(ci.get_enclosingmethod(), None)

        self.assertEqual(ci.get_innerclasses(), tuple())
        self.assertEqual(ci.get_annotations(), tuple())
        self.assertEqual(ci.get_invisible_annotations(), tuple())


    def test_abstract(self):
        ci = load("Sample2A")

        self.assertEqual(type(ci), jt.JavaClassInfo)

        self.assertEqual(ci.get_this(), "Sample2A")
        self.assertEqual(ci.pretty_this(), "Sample2A")

        self.assertEqual(ci.get_sourcefile(), "Sample2A.java")

        self.assertTrue(ci.is_public())
        self.assertTrue(ci.is_abstract())
        self.assertTrue(ci.is_super())

        self.assertFalse(ci.is_final())
        self.assertFalse(ci.is_interface())
        self.assertFalse(ci.is_annotation())
        self.assertFalse(ci.is_enum())
        self.assertFalse(ci.is_deprecated())

        self.assertEqual(ci.get_super(), "java/lang/Object")
        self.assertEqual(ci.pretty_super(), "java.lang.Object")

        # not a generic class, no signature
        self.assertEqual(ci.get_signature(), None)
        self.assertEqual(ci.pretty_signature(), None)

        self.assertEqual(ci.pretty_descriptor(),
                         "public abstract class Sample2A"
                         " extends java.lang.Object"
                         " implements Sample2I")

        self.assertEqual(ci.get_interfaces(), ("Sample2I",))
        self.assertEqual(tuple(ci.pretty_interfaces()), ("Sample2I",))

        # not an inner class, so no enclosing method
        self.assertEqual(ci.get_enclosingmethod(), None)

        self.assertEqual(ci.get_innerclasses(), tuple())
        self.assertEqual(ci.get_annotations(), tuple())
        self.assertEqual(ci.get_invisible_annotations(), tuple())


    def test_abstract_methods(self):
        ci = load("Sample2A")
        mi = ci.get_method("getSample")

        self.assertEqual(type(mi), jt.JavaMemberInfo)

        self.assertEqual(mi.get_name(), "getSample")
        self.assertEqual(mi.get_type_descriptor(), "LSample2A;")
        self.assertEqual(mi.get_descriptor(), "()LSample2A;")
        self.assertEqual(mi.get_identifier(), "getSample()")
        self.assertEqual(mi.pretty_type(), "Sample2A")
        self.assertEqual(mi.pretty_descriptor(),
                         "public Sample2A getSample()")
        self.assertEqual(mi.pretty_identifier(),
                         "getSample():Sample2A")

        self.assertTrue(mi.is_public())
        self.assertTrue(mi.is_method)

        self.assertFalse(mi.is_private())
        self.assertFalse(mi.is_protected())
        self.assertFalse(mi.is_static())
        self.assertFalse(mi.is_final())
        self.assertFalse(mi.is_synchronized())
        self.assertFalse(mi.is_native())
        self.assertFalse(mi.is_abstract())
        self.assertFalse(mi.is_strict())
        self.assertFalse(mi.is_volatile())
        self.assertFalse(mi.is_transient())
        self.assertFalse(mi.is_bridge())
        self.assertFalse(mi.is_varargs())
        self.assertFalse(mi.is_synthetic())
        self.assertFalse(mi.is_enum())
        self.assertFalse(mi.is_module())
        self.assertFalse(mi.is_deprecated())


    def test_abstract_method_bridges(self):
        ci = load("Sample2A")

        bis = tuple(ci.get_method_bridges("getSample"))
        self.assertEqual(len(bis), 1)

        mi = bis[0]
        self.assertEqual(type(mi), jt.JavaMemberInfo)

        self.assertEqual(mi.get_name(), "getSample")
        self.assertEqual(mi.get_type_descriptor(), "LSample2I;")
        self.assertEqual(mi.get_descriptor(), "()LSample2I;")
        self.assertEqual(mi.get_identifier(),
                         "getSample():()LSample2I;")
        self.assertEqual(mi.pretty_type(), "Sample2I")
        self.assertEqual(mi.pretty_descriptor(),
                         "public Sample2I getSample()")
        self.assertEqual(mi.pretty_identifier(),
                         "getSample():Sample2I")

        self.assertTrue(mi.is_public())
        self.assertTrue(mi.is_volatile())
        self.assertTrue(mi.is_bridge())
        self.assertTrue(mi.is_synthetic())
        self.assertTrue(mi.is_method)

        self.assertFalse(mi.is_private())
        self.assertFalse(mi.is_protected())
        self.assertFalse(mi.is_static())
        self.assertFalse(mi.is_final())
        self.assertFalse(mi.is_synchronized())
        self.assertFalse(mi.is_native())
        self.assertFalse(mi.is_abstract())
        self.assertFalse(mi.is_strict())
        self.assertFalse(mi.is_transient())
        self.assertFalse(mi.is_varargs())
        self.assertFalse(mi.is_enum())
        self.assertFalse(mi.is_module())
        self.assertFalse(mi.is_deprecated())


    def test_classinfo(self):
        ci = load("Sample2")

        self.assertEqual(type(ci), jt.JavaClassInfo)

        self.assertEqual(ci.get_this(), "Sample2")
        self.assertEqual(ci.pretty_this(), "Sample2")

        self.assertEqual(ci.get_sourcefile(), "Sample2.java")

        self.assertTrue(ci.is_public())
        self.assertTrue(ci.is_final())
        self.assertTrue(ci.is_super())

        self.assertFalse(ci.is_interface())
        self.assertFalse(ci.is_abstract())
        self.assertFalse(ci.is_annotation())
        self.assertFalse(ci.is_enum())
        self.assertFalse(ci.is_deprecated())

        self.assertEqual(ci.get_super(), "Sample2A")
        self.assertEqual(ci.pretty_super(), "Sample2A")

        # not a generic class, no signature
        self.assertEqual(ci.get_signature(), None)
        self.assertEqual(ci.pretty_signature(), None)

        self.assertEqual(ci.pretty_descriptor(),
                         "public final class Sample2"
                         " extends Sample2A")

        # even though it extends an abstract which implements
        # interfaces this class doesn't EXPLICITLY claim any
        # interfaces, so there are none in the classfile ... it's
        # added at runtime.
        self.assertEqual(ci.get_interfaces(), tuple())
        self.assertEqual(tuple(ci.pretty_interfaces()), tuple())

        # not an inner class, so no enclosing method
        self.assertEqual(ci.get_enclosingmethod(), None)

        self.assertEqual(ci.get_innerclasses(), tuple())
        self.assertEqual(ci.get_annotations(), tuple())
        self.assertEqual(ci.get_invisible_annotations(), tuple())


    def test_class_methods(self):
        ci = load("Sample2")
        mi = ci.get_method("getSample")

        self.assertEqual(type(mi), jt.JavaMemberInfo)

        self.assertEqual(mi.get_name(), "getSample")
        self.assertEqual(mi.get_type_descriptor(), "LSample2;")
        self.assertEqual(mi.get_descriptor(), "()LSample2;")
        self.assertEqual(mi.get_identifier(), "getSample()")
        self.assertEqual(mi.pretty_type(), "Sample2")
        self.assertEqual(mi.pretty_descriptor(),
                         "public Sample2 getSample()")
        self.assertEqual(mi.pretty_identifier(),
                         "getSample():Sample2")

        self.assertTrue(mi.is_public())
        self.assertTrue(mi.is_method)

        self.assertFalse(mi.is_private())
        self.assertFalse(mi.is_protected())
        self.assertFalse(mi.is_static())
        self.assertFalse(mi.is_final())
        self.assertFalse(mi.is_synchronized())
        self.assertFalse(mi.is_native())
        self.assertFalse(mi.is_abstract())
        self.assertFalse(mi.is_strict())
        self.assertFalse(mi.is_volatile())
        self.assertFalse(mi.is_transient())
        self.assertFalse(mi.is_bridge())
        self.assertFalse(mi.is_varargs())
        self.assertFalse(mi.is_synthetic())
        self.assertFalse(mi.is_enum())
        self.assertFalse(mi.is_module())
        self.assertFalse(mi.is_deprecated())


    def test_class_method_bridges(self):
        ci = load("Sample2")

        # Sample2 extends Sample2A which implements Sample2I, and each
        # level has its own getSample definition with a different,
        # more specific, return type. This results in Sample2 having
        # two bridges.
        bis = tuple(ci.get_method_bridges("getSample"))
        self.assertEqual(len(bis), 2)

        mi = bis[0]
        self.assertEqual(type(mi), jt.JavaMemberInfo)

        self.assertEqual(mi.get_name(), "getSample")
        self.assertEqual(mi.get_type_descriptor(), "LSample2A;")
        self.assertEqual(mi.get_descriptor(), "()LSample2A;")
        self.assertEqual(mi.get_identifier(),
                         "getSample():()LSample2A;")
        self.assertEqual(mi.pretty_type(), "Sample2A")
        self.assertEqual(mi.pretty_descriptor(),
                         "public Sample2A getSample()")
        self.assertEqual(mi.pretty_identifier(),
                         "getSample():Sample2A")

        self.assertTrue(mi.is_public())
        self.assertTrue(mi.is_volatile())
        self.assertTrue(mi.is_bridge())
        self.assertTrue(mi.is_synthetic())
        self.assertTrue(mi.is_method)

        self.assertFalse(mi.is_private())
        self.assertFalse(mi.is_protected())
        self.assertFalse(mi.is_static())
        self.assertFalse(mi.is_final())
        self.assertFalse(mi.is_synchronized())
        self.assertFalse(mi.is_native())
        self.assertFalse(mi.is_abstract())
        self.assertFalse(mi.is_strict())
        self.assertFalse(mi.is_transient())
        self.assertFalse(mi.is_varargs())
        self.assertFalse(mi.is_enum())
        self.assertFalse(mi.is_module())
        self.assertFalse(mi.is_deprecated())

        mi = bis[1]
        self.assertEqual(type(mi), jt.JavaMemberInfo)

        self.assertEqual(mi.get_name(), "getSample")
        self.assertEqual(mi.get_type_descriptor(), "LSample2I;")
        self.assertEqual(mi.get_descriptor(), "()LSample2I;")
        self.assertEqual(mi.get_identifier(),
                         "getSample():()LSample2I;")
        self.assertEqual(mi.pretty_type(), "Sample2I")
        self.assertEqual(mi.pretty_descriptor(),
                         "public Sample2I getSample()")
        self.assertEqual(mi.pretty_identifier(),
                         "getSample():Sample2I")

        self.assertTrue(mi.is_public())
        self.assertTrue(mi.is_volatile())
        self.assertTrue(mi.is_bridge())
        self.assertTrue(mi.is_synthetic())
        self.assertTrue(mi.is_method)

        self.assertFalse(mi.is_private())
        self.assertFalse(mi.is_protected())
        self.assertFalse(mi.is_static())
        self.assertFalse(mi.is_final())
        self.assertFalse(mi.is_synchronized())
        self.assertFalse(mi.is_native())
        self.assertFalse(mi.is_abstract())
        self.assertFalse(mi.is_strict())
        self.assertFalse(mi.is_transient())
        self.assertFalse(mi.is_varargs())
        self.assertFalse(mi.is_enum())
        self.assertFalse(mi.is_module())
        self.assertFalse(mi.is_deprecated())


class Sample3Test(TestCase):

    def test_classinfo(self):
        ci = load("Sample3")

        self.assertEqual(type(ci), jt.JavaClassInfo)

        self.assertEqual(ci.get_this(), "Sample3")
        self.assertEqual(ci.pretty_this(), "Sample3")

        self.assertEqual(ci.get_sourcefile(), "Sample3.java")

        self.assertTrue(ci.is_public())
        self.assertTrue(ci.is_super())

        self.assertFalse(ci.is_interface())
        self.assertFalse(ci.is_abstract())
        self.assertFalse(ci.is_final())
        self.assertFalse(ci.is_annotation())
        self.assertFalse(ci.is_enum())
        self.assertFalse(ci.is_deprecated())

        self.assertEqual(ci.get_super(), "java/lang/Object")
        self.assertEqual(ci.pretty_super(), "java.lang.Object")

        self.assertEqual(ci.get_signature(), None)
        self.assertEqual(ci.pretty_signature(), None)

        self.assertEqual(ci.pretty_descriptor(),
                         "public class Sample3 extends java.lang.Object")

        self.assertEqual(ci.get_interfaces(), tuple())
        self.assertEqual(tuple(ci.pretty_interfaces()), tuple())

        self.assertEqual(ci.get_enclosingmethod(), None)

        self.assertEqual(ci.get_innerclasses(), tuple())
        self.assertEqual(ci.get_annotations(), tuple())
        self.assertEqual(ci.get_invisible_annotations(), tuple())


    def test_field_data(self):
        ci = load("Sample3")
        fi = ci.get_field_by_name("data")

        self.assertEqual(type(fi), jt.JavaMemberInfo)

        self.assertEqual(fi.get_name(), "data")
        self.assertEqual(fi.get_type_descriptor(),
                         "Ljava/lang/Object;")
        self.assertEqual(fi.get_descriptor(),
                         "Ljava/lang/Object;")
        self.assertEqual(fi.pretty_type(),
                         "java.lang.Object")
        self.assertEqual(fi.pretty_descriptor(),
                         "private java.lang.Object data")

        self.assertTrue(fi.is_private())

        self.assertFalse(fi.is_public())
        self.assertFalse(fi.is_protected())
        self.assertFalse(fi.is_static())
        self.assertFalse(fi.is_final())
        self.assertFalse(fi.is_synchronized())
        self.assertFalse(fi.is_native())
        self.assertFalse(fi.is_abstract())
        self.assertFalse(fi.is_strict())
        self.assertFalse(fi.is_volatile())
        self.assertFalse(fi.is_transient())
        self.assertFalse(fi.is_bridge())
        self.assertFalse(fi.is_varargs())
        self.assertFalse(fi.is_synthetic())
        self.assertFalse(fi.is_enum())
        self.assertFalse(fi.is_module())
        self.assertFalse(fi.is_deprecated())
        self.assertFalse(fi.is_method)

        self.assertEqual(fi.deref_constantvalue(), None)

        fi = ci.get_field_by_name("twoDimIntArray")
        self.assertEqual(fi.pretty_type(),
                         "int[][]")


    def test_field_recent_name(self):
        ci = load("Sample3")
        fi = ci.get_field_by_name("lastData")

        self.assertEqual(type(fi), jt.JavaMemberInfo)

        self.assertEqual(fi.get_name(), "lastData")
        self.assertEqual(fi.get_type_descriptor(),
                         "Ljava/lang/Object;")
        self.assertEqual(fi.get_descriptor(),
                         "Ljava/lang/Object;")
        self.assertEqual(fi.pretty_type(),
                         "java.lang.Object")
        self.assertEqual(fi.pretty_descriptor(),
                         "private static java.lang.Object lastData")

        self.assertTrue(fi.is_private())
        self.assertTrue(fi.is_static())

        self.assertFalse(fi.is_public())
        self.assertFalse(fi.is_protected())
        self.assertFalse(fi.is_final())
        self.assertFalse(fi.is_synchronized())
        self.assertFalse(fi.is_native())
        self.assertFalse(fi.is_abstract())
        self.assertFalse(fi.is_strict())
        self.assertFalse(fi.is_volatile())
        self.assertFalse(fi.is_transient())
        self.assertFalse(fi.is_bridge())
        self.assertFalse(fi.is_varargs())
        self.assertFalse(fi.is_synthetic())
        self.assertFalse(fi.is_enum())
        self.assertFalse(fi.is_module())
        self.assertFalse(fi.is_deprecated())
        self.assertFalse(fi.is_method)

        self.assertEqual(fi.deref_constantvalue(), None)


    def test_method_get_data(self):
        ci = load("Sample3")
        mi = ci.get_method("getData")

        self.assertEqual(type(mi), jt.JavaMemberInfo)

        self.assertEqual(mi.get_name(), "getData")
        self.assertEqual(mi.get_type_descriptor(), "Ljava/lang/Object;")
        self.assertEqual(mi.get_descriptor(), "()Ljava/lang/Object;")
        self.assertEqual(mi.get_identifier(), "getData()")
        self.assertEqual(mi.pretty_type(), "java.lang.Object")
        self.assertEqual(mi.pretty_descriptor(),
                         "public synchronized java.lang.Object getData()"
                         " throws java.lang.Exception")
        self.assertEqual(mi.pretty_identifier(),
                         "getData():java.lang.Object")

        self.assertTrue(mi.is_public())
        self.assertTrue(mi.is_synchronized())
        self.assertTrue(mi.is_method)

        self.assertFalse(mi.is_private())
        self.assertFalse(mi.is_protected())
        self.assertFalse(mi.is_static())
        self.assertFalse(mi.is_final())
        self.assertFalse(mi.is_native())
        self.assertFalse(mi.is_abstract())
        self.assertFalse(mi.is_strict())
        self.assertFalse(mi.is_volatile())
        self.assertFalse(mi.is_transient())
        self.assertFalse(mi.is_bridge())
        self.assertFalse(mi.is_varargs())
        self.assertFalse(mi.is_synthetic())
        self.assertFalse(mi.is_enum())
        self.assertFalse(mi.is_module())
        self.assertFalse(mi.is_deprecated())

        excs = mi.get_exceptions()
        self.assertEqual(excs, ("java/lang/Exception",))

        excs = tuple(mi.pretty_exceptions())
        self.assertEqual(excs, ("java.lang.Exception",))


    def test_method_get_data_default(self):
        ci = load("Sample3")
        mi = ci.get_method("getData", ["Ljava/lang/Object;"])

        self.assertEqual(type(mi), jt.JavaMemberInfo)

        self.assertEqual(mi.get_name(), "getData")
        self.assertEqual(mi.get_type_descriptor(), "Ljava/lang/Object;")
        self.assertEqual(mi.get_descriptor(),
                         "(Ljava/lang/Object;)Ljava/lang/Object;")
        self.assertEqual(mi.get_identifier(),
                         "getData(Ljava/lang/Object;)")
        self.assertEqual(mi.pretty_type(), "java.lang.Object")
        self.assertEqual(mi.pretty_descriptor(),
                         "public java.lang.Object"
                         " getData(java.lang.Object)")
        self.assertEqual(mi.pretty_identifier(),
                         "getData(java.lang.Object):java.lang.Object")

        self.assertTrue(mi.is_public())
        self.assertTrue(mi.is_method)

        self.assertFalse(mi.is_private())
        self.assertFalse(mi.is_protected())
        self.assertFalse(mi.is_static())
        self.assertFalse(mi.is_synchronized())
        self.assertFalse(mi.is_final())
        self.assertFalse(mi.is_native())
        self.assertFalse(mi.is_abstract())
        self.assertFalse(mi.is_strict())
        self.assertFalse(mi.is_volatile())
        self.assertFalse(mi.is_transient())
        self.assertFalse(mi.is_bridge())
        self.assertFalse(mi.is_varargs())
        self.assertFalse(mi.is_synthetic())
        self.assertFalse(mi.is_enum())
        self.assertFalse(mi.is_module())
        self.assertFalse(mi.is_deprecated())

        excs = mi.get_exceptions()
        self.assertEqual(excs, tuple())

        excs = tuple(mi.pretty_exceptions())
        self.assertEqual(excs, tuple())

        code = mi.get_code()
        code_excs = code.exceptions

        self.assertEqual(len(code_excs), 1)

        ce = code_excs[0]
        self.assertEqual(type(ce), jt.JavaExceptionInfo)

        self.assertEqual(ce.get_catch_type(), "java/lang/Exception")
        self.assertEqual(ce.pretty_catch_type(), "Class java.lang.Exception")

        self.assertEqual(ce.info(), (0, 4, 5, "java/lang/Exception"))


    def test_method_set_data(self):
        ci = load("Sample3")
        mi = ci.get_method("setData", ["Ljava/lang/Object;"])

        self.assertEqual(type(mi), jt.JavaMemberInfo)

        self.assertEqual(mi.get_name(), "setData")
        self.assertEqual(mi.get_type_descriptor(), "V")
        self.assertEqual(mi.get_descriptor(),
                         "(Ljava/lang/Object;)V")
        self.assertEqual(mi.get_identifier(),
                         "setData(Ljava/lang/Object;)")
        self.assertEqual(mi.pretty_type(), "void")
        self.assertEqual(mi.pretty_descriptor(),
                         "public synchronized void"
                         " setData(java.lang.Object)")
        self.assertEqual(mi.pretty_identifier(),
                         "setData(java.lang.Object):void")

        self.assertTrue(mi.is_public())
        self.assertTrue(mi.is_synchronized())
        self.assertTrue(mi.is_method)

        self.assertFalse(mi.is_private())
        self.assertFalse(mi.is_protected())
        self.assertFalse(mi.is_static())
        self.assertFalse(mi.is_final())
        self.assertFalse(mi.is_native())
        self.assertFalse(mi.is_abstract())
        self.assertFalse(mi.is_strict())
        self.assertFalse(mi.is_volatile())
        self.assertFalse(mi.is_transient())
        self.assertFalse(mi.is_bridge())
        self.assertFalse(mi.is_varargs())
        self.assertFalse(mi.is_synthetic())
        self.assertFalse(mi.is_enum())
        self.assertFalse(mi.is_module())
        self.assertFalse(mi.is_deprecated())

        excs = mi.get_exceptions()
        self.assertEqual(excs, tuple())

        excs = tuple(mi.pretty_exceptions())
        self.assertEqual(excs, tuple())


    def test_method_get_last_data(self):
        ci = load("Sample3")
        mi = ci.get_method("getLastData")

        self.assertEqual(type(mi), jt.JavaMemberInfo)

        self.assertEqual(mi.get_name(), "getLastData")
        self.assertEqual(mi.get_type_descriptor(), "Ljava/lang/Object;")
        self.assertEqual(mi.get_descriptor(), "()Ljava/lang/Object;")
        self.assertEqual(mi.get_identifier(), "getLastData()")
        self.assertEqual(mi.pretty_type(), "java.lang.Object")
        self.assertEqual(mi.pretty_descriptor(),
                         "private static synchronized java.lang.Object"
                         " getLastData()"
                         " throws java.lang.Exception")
        self.assertEqual(mi.pretty_identifier(),
                         "getLastData():java.lang.Object")

        self.assertTrue(mi.is_private())
        self.assertTrue(mi.is_static())
        self.assertTrue(mi.is_synchronized())
        self.assertTrue(mi.is_method)

        self.assertFalse(mi.is_public())
        self.assertFalse(mi.is_protected())
        self.assertFalse(mi.is_final())
        self.assertFalse(mi.is_native())
        self.assertFalse(mi.is_abstract())
        self.assertFalse(mi.is_strict())
        self.assertFalse(mi.is_volatile())
        self.assertFalse(mi.is_transient())
        self.assertFalse(mi.is_bridge())
        self.assertFalse(mi.is_varargs())
        self.assertFalse(mi.is_synthetic())
        self.assertFalse(mi.is_enum())
        self.assertFalse(mi.is_module())
        self.assertFalse(mi.is_deprecated())

        excs = mi.get_exceptions()
        self.assertEqual(excs, ("java/lang/Exception",))

        excs = tuple(mi.pretty_exceptions())
        self.assertEqual(excs, ("java.lang.Exception",))


    def test_method_set_last_data(self):
        ci = load("Sample3")
        mi = ci.get_method("setLastData", ["Ljava/lang/Object;"])

        self.assertEqual(type(mi), jt.JavaMemberInfo)

        self.assertEqual(mi.get_name(), "setLastData")
        self.assertEqual(mi.get_type_descriptor(), "V")
        self.assertEqual(mi.get_descriptor(),
                         "(Ljava/lang/Object;)V")
        self.assertEqual(mi.get_identifier(),
                         "setLastData(Ljava/lang/Object;)")
        self.assertEqual(mi.pretty_type(), "void")
        self.assertEqual(mi.pretty_descriptor(),
                         "private static synchronized void"
                         " setLastData(java.lang.Object)")
        self.assertEqual(mi.pretty_identifier(),
                         "setLastData(java.lang.Object):void")

        self.assertTrue(mi.is_private())
        self.assertTrue(mi.is_static())
        self.assertTrue(mi.is_synchronized())
        self.assertTrue(mi.is_method)

        self.assertFalse(mi.is_public())
        self.assertFalse(mi.is_protected())
        self.assertFalse(mi.is_final())
        self.assertFalse(mi.is_native())
        self.assertFalse(mi.is_abstract())
        self.assertFalse(mi.is_strict())
        self.assertFalse(mi.is_volatile())
        self.assertFalse(mi.is_transient())
        self.assertFalse(mi.is_bridge())
        self.assertFalse(mi.is_varargs())
        self.assertFalse(mi.is_synthetic())
        self.assertFalse(mi.is_enum())
        self.assertFalse(mi.is_module())
        self.assertFalse(mi.is_deprecated())

        excs = mi.get_exceptions()
        self.assertEqual(excs, tuple())

        excs = tuple(mi.pretty_exceptions())
        self.assertEqual(excs, tuple())


#
# The end.
