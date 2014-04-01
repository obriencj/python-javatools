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
import pkg_resources


def get_class_fn(which):
    which = "data/%s.class" % which
    fn = pkg_resources.resource_filename(__name__, which)
    return fn


def load(which):
    fn = get_class_fn(which)
    return jt.unpack_classfile(fn)


class ClassfileTest(TestCase):


    def test_is_class_file(self):
        fn = get_class_fn("Sample1")

        with open(fn, "rb") as fd:
            magic = fd.read(4)

        self.assertTrue(jt.is_class_file(fn))


    def test_sample1_classinfo(self):
        ci = load("Sample1")

        self.assertEqual(type(ci), jt.JavaClassInfo)

        self.assertEqual(ci.get_this(), "Sample1")
        self.assertEqual(ci.pretty_this(), "Sample1")

        self.assertEqual(ci.get_sourcefile(), "Sample1.java")

        self.assertTrue(ci.is_public())
        self.assertFalse(ci.is_final())

        self.assertFalse(ci.is_interface())
        self.assertFalse(ci.is_abstract())

        self.assertTrue(ci.is_super())

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


    def test_sample1_field_name(self):
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
        self.assertFalse(fi.is_public())
        self.assertTrue(fi.is_private())
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


    def test_sample1_field_recent_name(self):
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
        self.assertFalse(fi.is_public())
        self.assertFalse(fi.is_private())
        self.assertTrue(fi.is_protected())
        self.assertTrue(fi.is_static())
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


    def test_sample1_field_default_name(self):
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
        self.assertFalse(fi.is_private())
        self.assertFalse(fi.is_protected())
        self.assertTrue(fi.is_static())
        self.assertTrue(fi.is_final())
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

        self.assertEqual(fi.deref_constantvalue(),
                         "Daphne")


    def test_sample1_methods(self):
        ci = load("Sample1")


#
# The end.
