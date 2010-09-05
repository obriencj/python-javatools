"""

Utility script for comparing the internals of two Java class files for
differences in structure and data. Has options to specify changes
which may be immaterial or unimportant, such as re-ordering of the
constant pool, line number changes (either absolute or relative),
added fields or methods, deprecation changes, etc.

author: Christopher O'Brien  <obriencj@gmail.com>

"""



import sys
from change import Change, GenericChange, SuperChange



# NO_CHANGE = 0
# CLASS_DATA_CHANGE = 1 << 1
# FIELD_DATA_CHANGE = 1 << 2
# METHOD_DATA_CHANGE = 1 << 3
# CONST_DATA_CHANGE = 1 << 4



# LEFT = "left"
# RIGHT = "right"
# BOTH = "both"



class ClassNameChange(GenericChange):
    label = "Class name"

    
    def fn_data(self, c):
        return c.get_this()


    def fn_pretty(self, c):
        return c.pretty_this()



class ClassVersionChange(GenericChange):
    label = "Java class verison"


    def fn_data(self, c):
        return c.version


    def is_ignored(self, o):
        lver, rver = self.ldata.version, self.rdata.version
        return ((o.ignore_version_up and lver < rver) or
                (o.ignore_version_down and lver > rver))



class ClassPlatformChange(GenericChange):
    label = "Java platform"


    def fn_data(self, c):
        return c.get_platform()


    def is_ignored(self, o):
        lver, rver = self.ldata.version, self.rdata.version
        return ((o.ignore_version_up and lver < rver) or
                (o.ignore_version_down and lver > rver))



class ClassSuperclassChange(GenericChange):
    label = "Superclass"


    def fn_data(self, c):
        return c.get_super()


    def fn_pretty(self, c):
        return c.pretty_super()



class ClassInterfacesChange(GenericChange):
    label = "Interfaces"


    def fn_data(self, c):
        return set(c.get_interfaces())
    


class ClassAccessflagsChange(GenericChange):
    label = "Access flags"


    def fn_data(self, c):
        return c.access_flags


    def fn_pretty(self, c):
        return c.pretty_access_flags()



class ClassDeprecationChange(GenericChange):
    label = "Deprecation"


    def fn_data(self, c):
        return c.is_deprecated()


    def is_ignored(self, o):
        return o.ignore_deprecated



class ClassInfoChange(SuperChange):
    label = "Class information"

    change_types = (ClassNameChange,
                    ClassVersionChange,
                    ClassPlatformChange,
                    ClassSuperclassChange,
                    ClassInterfacesChange,
                    ClassAccessflagsChange,
                    ClassDeprecationChange)



class MemberSuperChange(SuperChange):
    
    """ basis for FieldChange and MethodChange """
    
    label = "Member changed"


    def get_description(self):
        return "%s %s" % (self.label, self.ldata.pretty_descriptor())



class MemberAdded(Change):
    
    """ basis for FieldAdded and MethodAdded """
    
    label = "Member added"


    def is_change(self):
        return True


    def get_description(self):
        return "%s %s" % (self.label, self.rdata.pretty_descriptor())



class MemberRemoved(Change):
    
    """ basis for FieldChange and MethodChange """
    
    label = "Member removed"


    def is_change(self):
        return True


    def get_description(self):
        return "%s %s" % (self.label, self.ldata.pretty_descriptor())



class ClassMembersChange(SuperChange):

    """ basis for ClassFieldsChange and ClassMethodsChange """
    
    label = "Members"

    member_added = MemberAdded
    member_removed = MemberRemoved
    member_changed = MemberSuperChange

    
    def changes_impl(self):
        li = {}
        
        for member in self.ldata:
            li[member.get_identifier()] = member
    
        for member in self.rdata:
            key = member.get_identifier()
            lf = li.get(key, None)

            if lf:
                del li[key]
                yield self.member_changed(lf, member)
            else:
                yield self.member_added(None, member)
    
        for member in li.values():
            yield self.member_removed(member, None)


    

class CodeAbsoluteChange(GenericChange):
    label = "Absolute line numbers"


    def fn_data(self, c):
        return c.get_linenumbertable()


    def is_ignored(self, options):
        return options.ignore_absolute_lines
    


class CodeRelativeChange(GenericChange):
    label = "Relative line numbers"


    def fn_data(self, c):
        return c.get_relativelinenumbertable()
    
        
    def is_ignored(self, options):
        return options.ignore_relative_lines



class CodeStackChange(GenericChange):
    label = "Stack size"


    def fn_data(self, c):
        return c.max_stack

    

class CodeLocalsChange(GenericChange):
    label = "Locals"


    def fn_data(self, c):
        return c.max_locals



class CodeExceptionChange(GenericChange):
    label = "Exception table"


    def fn_data(self, c):
        return c.exceptions



class CodeConstantsChange(GenericChange):
    label = "Code constants"


    def check_impl(self):
        import opcodes
        
        left,right = self.ldata, self.rdata

        if len(left.code) != len(right.code):
            # code body change, can't determine constants
            return False, None
        
        for l,r in zip(left.disassemble(), right.disassemble()):
            if not ((l[0] == r[0]) and (l[1] == r[1])):
                # code body change, can't determine constants
                return False, None
            
            largs,rargs = l[2], r[2]
            if opcodes.has_const_arg(l[1]):
                largs, rargs = list(largs), list(rargs)
                largs[0] = left.deref_const(largs[0])
                rargs[0] = right.deref_const(rargs[0])

            if largs != rargs:
                return True, None

        return False, None
        


class CodeBodyChange(GenericChange):
    label = "Code body"


    def check_impl(self):
        left,right = self.ldata,self.rdata
                
        if len(left.code) != len(right.code):
            desc = "Code length changed from %r to %r" % \
                   (len(left.code), len(right.code))
            return True, desc

        for l,r in zip(left.disassemble(), right.disassemble()):
            if not ((l[0] == r[0]) and (l[1] == r[1])):
                return True, None

        return False, None



class MethodNameChange(GenericChange):
    label = "Method name"


    def fn_data(self, c):
        return c.get_name()
    
    

class MethodTypeChange(GenericChange):
    label = "Method type"


    def fn_data(self, c):
        return c.get_type_descriptor()


    def fn_pretty(self, c):
        return c.pretty_type()
        


class MethodParametersChange(GenericChange):
    label = "Method parameters"


    def fn_data(self, c):
        return c.get_arg_type_descriptors()


    def fn_pretty(self, c):
        return ",".join(c.pretty_arg_types())

    

class MethodAccessflagsChange(GenericChange):
    label = "Method accessflags"


    def fn_data(self, c):
        return c.access_flags


    def fn_pretty(self, c):
        return ",".join(c.pretty_access_flags())



class MethodAbstractChange(GenericChange):
    label = "Method abstract"


    def fn_data(self, c):
        return (not c.get_code())



class MethodExceptionsChange(GenericChange):
    label = "Method exceptions"


    def fn_data(self, c):
        return c.get_exceptions()


    def fn_pretty(self, c):
        return ",".join(c.pretty_exceptions())
        


class MethodCodeChange(SuperChange):
    label = "Method code"


    change_types = (CodeAbsoluteChange,
                    CodeRelativeChange,
                    CodeStackChange,
                    CodeLocalsChange,
                    CodeExceptionChange,
                    CodeConstantsChange,
                    CodeBodyChange)


    def __init__(self,l,r):
        SuperChange.__init__(self,l.get_code(),r.get_code())


    def check_impl(self):
        if None not in (self.ldata, self.rdata):
            return SuperChange.check_impl(self)
        else:
            return (self.ldata == self.rdata), None
        
            

class MethodChange(MemberSuperChange):
    label = "Method"
    

    change_types = (MethodNameChange,
                    MethodTypeChange,
                    MethodParametersChange,
                    MethodAccessflagsChange,
                    MethodExceptionsChange,
                    MethodAbstractChange,
                    MethodCodeChange)
    


class FieldNameChange(GenericChange):
    label = "Field name"


    def fn_data(self, c):
        return c.get_name()



class FieldTypeChange(GenericChange):
    label = "Field type"


    def fn_data(self, c):
        return c.get_descriptor()


    def fn_pretty(self, c):
        return c.pretty_type()



class FieldAccessflagsChange(GenericChange):
    label = "Field accessflags"


    def fn_data(self, c):
        return c.access_flags


    def fn_pretty(self, c):
        return ",".join(c.pretty_access_flags())



class FieldConstvalueChange(GenericChange):
    label = "Field constvalue"


    def fn_data(self, c):
        return c.deref_const()



class FieldChange(MemberSuperChange):
    label = "Field"


    change_types = (FieldNameChange,
                    FieldTypeChange,
                    FieldAccessflagsChange,
                    FieldConstvalueChange)

        

class FieldAdded(MemberAdded):
    label = "Field added"



class FieldRemoved(MemberRemoved):
    label = "Field removed"

    

class ClassFieldsChange(ClassMembersChange):
    label = "Fields"

    member_added = FieldAdded
    member_removed = FieldRemoved
    member_changed = FieldChange


    def __init__(self, lclass, rclass):
        ClassMembersChange.__init__(self, lclass.fields, rclass.fields)



class MethodAdded(MemberAdded):
    label = "Method added"



class MethodRemoved(MemberRemoved):
    label = "Method removed"



class ClassMethodsChange(ClassMembersChange):
    label = "Methods"

    member_added = MethodAdded
    member_removed = MethodRemoved
    member_changed = MethodChange


    def __init__(self,lclass,rclass):
        ClassMembersChange.__init__(self,lclass.methods,rclass.methods)



class JavaClassChange(SuperChange):

    label = "Class"


    change_types = (ClassInfoChange,
                    ClassFieldsChange,
                    ClassMethodsChange)


    def get_description(self):
        return "%s %s" % (self.label, self.ldata.pretty_descriptor())




# def cli_compare_class(options, left, right):
#     from javaclass import JavaClassInfo

#     if not (isinstance(left, JavaClassInfo) and
#             isinstance(right, JavaClassInfo)):
#         raise TypeError("wanted JavaClassInfo")

#     ret = NO_CHANGE

#     # name
#     if left.get_this() != right.get_this():
#         print "Class name changed: %s to %s" % \
#             (left.pretty_this(), right.pretty_this())
#         ret = CLASS_DATA_CHANGE

#     # version
#     lver, rver = left.version, right.version
#     if lver != rver:
#         if ((not options.ignore_version_up and lver < rver) and
#             (not options.ignore_version_down and lver > rver)):
#             print "Java class version changed: %r to %r" % (lver, rver)
#             ret = CLASS_DATA_CHANGE
            
#     # platform
#     lplat, rplat = left.get_platform(), right.get_platform()
#     if lplat != rplat:
#         if ((not options.ignore_platform_up and lver < rver) and
#             (not options.ignore_platform_down and lver > rver)):
#             print "Java platform changed: %s to %s" % (lplat, rplat)
#             ret = CLASS_DATA_CHANGE

#     # inheritance
#     if left.get_super() != right.get_super():
#         print "Superclass changed: %s to %s" % \
#             (left.pretty_super(), right.pretty_super())

#     # interfaces
#     li, ri = set(left.get_interfaces()), set(right.get_interfaces())
#     if li != ri:
#         print "Interfaces changed: (%s) to (%s)" % \
#             (", ".join(li), ", ".join(ri))
#         ret = CLASS_DATA_CHANGE

#     # access flags
#     if left.access_flags != right.access_flags:
#         print "Access flags changed: %s to %s" % \
#             (left.pretty_access_flags(), right.pretty_access_flags())
#         ret = CLASS_DATA_CHANGE

#     # deprecation
#     if not options.ignore_deprecated and \
#             (left.is_deprecated() != right.is_deprecated()):
#         print "Deprecation became %s" % right.is_deprecated()
#         ret = CLASS_DATA_CHANGE

#     return ret



# def cli_members_diff(options, left_members, right_members):
    
#     """ generator yielding (EVENT, (left_meth, right_meth)) """

#     li = {}
#     for f in left_members:
#         #print " XXX l_memb:", f.get_identifier()
#         li[f.get_identifier()] = f

#     for f in right_members:
#         #print " XXX r_memb:", f.get_identifier()
#         key = f.get_identifier()
#         lf = li.get(key, None)

#         if lf:
#             del li[key]
#             yield (BOTH, (lf, f))
#         else:
#             yield (RIGHT, (None, f))
    
#     for f in li.values():
#         yield (LEFT, (f, None))
        


# def cli_collect_members_diff(options, l_members, r_members,
#                              added=None, removed=None, both=None):
    
#     for event,data in cli_members_diff(options, l_members, r_members):
#         l = None

#         if event is LEFT:
#             l = removed
#         elif event is RIGHT:
#             l = added
#         elif event is BOTH:
#             l = both
        
#         if l is not None:
#             l.append(data)

#     return added, removed, both



# def _cli_compare_field(options, left, right):
    
#     from javaclass import JavaMemberInfo
    
#     if not (isinstance(left, JavaMemberInfo) and
#             isinstance(right, JavaMemberInfo)):
#         raise TypeError("wanted JavaMemberInfo")
    
#     if left.get_name() != right.get_name():
#         yield "name changed from %s to %s" % \
#             (left.get_name(), right.get_name())
        
#     if left.get_descriptor() != right.get_descriptor():
#         yield "type chnaged from %s to %s" % \
#             (left.pretty_type(), right.pretty_type())

#     if left.access_flags != right.access_flags:
#         yield "access flags changed from (%s) to (%s)" % \
#             (",".join(left.pretty_access_flags()),
#              ",".join(right.pretty_access_flags()))
        
#     if left.deref_const() != right.deref_const():
#         yield "constant value changed"



# def cli_compare_field(options, left, right):

#     """ a sequence of changes (strings describing the change). Will be
#     empty if the fields are considered identical according to the
#     options passed """

#     return tuple(_cli_compare_field(options, left, right))



# def cli_compare_fields(options, left, right):

#     """ returns either NO_CHANGE or FIELD_DATA_CHANGE, and prints
#     detailed information to stdout """

#     ret = NO_CHANGE

#     added, removed, both = [], [], []

#     cli_collect_members_diff(options, left.fields, right.fields,
#                              added, removed, both)

#     ret = NO_CHANGE

#     if not options.ignore_added and added:
#         print "Added fields:"
#         for l,r in added:
#             print "  ", r.pretty_descriptor()
#         ret = FIELD_DATA_CHANGE

#     if removed:
#         print "Removed fields:"
#         for l,r in removed:
#             print "  ", l.pretty_descriptor()
#         ret = FIELD_DATA_CHANGE

#     def print_changed(field, changes, pc=[True]):
#         if pc[0]:
#             print "Changed fields:"
#             pc[0] = False

#         print "  ", field.pretty_descriptor()
#         for change in changes:
#             print "    ", change

#     if both:
#         for l,r in both:
#             changes = cli_compare_field(options, l, r)
#             if changes:
#                 print_changed(r, changes)
#                 ret = FIELD_DATA_CHANGE

#     return ret



# def relative_lnt(lnt):

#     """ given a LineNumberTable (just a sequence of int,int pairs)
#     produce a relative version (lines as offset from the first line in
#     the table) """

#     if lnt:
#         lineoff = lnt[0][1]
#         return [(o,l-lineoff) for (o,l) in lnt]
#     else:
#         return tuple()



# def _cli_compare_code(options, left, right):

#     from javaclass import JavaCodeInfo
#     import javaclass.opcodes as opcodes

#     if None in (left, right):
#         if left == right:
#             # both sides are probably abstract
#             pass
#         elif not left:
#             yield "code removed"
#         elif not right:
#             yield "code added"
#         return

#     if not (isinstance(left, JavaCodeInfo) and
#             isinstance(right, JavaCodeInfo)):
#         raise TypeError("wanted JavaCodeInfo")

#     l_lnt, r_lnt = left.get_linenumbertable(), right.get_linenumbertable()
#     if (not options.ignore_absolute_lines and l_lnt != r_lnt):
#         yield "absolute line numbers changed"

#     l_lnt, r_lnt = relative_lnt(l_lnt), relative_lnt(r_lnt)
#     if (not options.ignore_relative_lines and l_lnt != r_lnt):
#         yield "relative line numbers changed"

#     if left.max_stack != right.max_stack:
#         yield "max stack size changed from %i to %i" % \
#             (left.max_stack, right.max_stack)

#     if left.max_locals != right.max_locals:
#         yield "max locals changed from %i to %i" % \
#             (left.max_locals, right.max_locals)

#     if left.exceptions != right.exceptions:
#         yield "exception table changed"

#     if len(left.code) == len(right.code):
#         code_vals_change = False
#         code_body_change = False

#         for l,r in zip(left.disassemble(), right.disassemble()):
#             if not ((l[0] == r[0]) and (l[1] == r[1])):
#                 code_body_change = True
#                 break

#             largs, rargs = l[2], r[2]

#             if opcodes.has_const_arg(l[1]):
#                 largs, rargs = list(largs), list(rargs)
#                 largs[0] = left.cpool.deref_const(largs[0])
#                 rargs[0] = right.cpool.deref_const(rargs[0])

#             if largs != rargs:
#                 code_vals_change = True
#                 break

#         if code_vals_change:
#             yield "code constants changed"

#     else:
#         yield "code length changed from %i to %i" % \
#             (len(left.code), len(right.code))
#         code_body_change = True

#     if code_body_change:
#         yield "code body changed"



# def cli_compare_code(options, left, right):

#     """ a sequence of changes (strings describing the change). Will be
#     empty if the code bodies are considered identical according to the
#     options passed. This method is normally only called from within
#     cli_compare_method """

#     return [change for change in _cli_compare_code(options, left, right)]



# def _cli_compare_method(options, left, right):

#     from javaclass import JavaMemberInfo

#     if not (isinstance(left, JavaMemberInfo) and
#             isinstance(right, JavaMemberInfo)):
#         raise TypeError("wanted JavaMemberInfo")

#     if left.get_name() != right.get_name():
#         yield "name changed from %s to %s" % \
#             (left.get_name(), right.get_name())

#     if left.get_type_descriptor() != right.get_type_descriptor():
#         yield "return type changed from %s to %s" % \
#             (left.pretty_type(), right.pretty_type())

#     if left.get_arg_type_descriptors() != right.get_arg_type_descriptors():
#         yield "parameters changed from (%s) to (%s)" % \
#             (",".join(left.pretty_arg_types()),
#              ",".join(right.pretty_arg_types()))

#     if left.access_flags != right.access_flags:
#         yield "access flags changed from (%s) to (%s)" % \
#             (",".join(left.pretty_access_flags()),
#              ",".join(right.pretty_access_flags()))

#     if set(left.get_exceptions()) != set(right.get_exceptions()):
#         yield "exceptions changed from (%s) to (%s)" % \
#             (",".join(left.pretty_exceptions()),
#              ",".join(right.pretty_exceptions()))

#     for c in _cli_compare_code(options, left.get_code(), right.get_code()):
#         yield c
        


# def cli_compare_method(options, left, right):

#     """ a sequence of changes (strings describing the change). Will be
#     empty if the methods are considered identical according to the
#     options passed """

#     return [change for change in _cli_compare_method(options, left, right)]



# def cli_compare_methods(options, left, right):
    
#     """ returns either NO_CHANGE or METHOD_DATA_CHANGE, and prints out
#     detailed information on any changes to stdout """

#     added, removed, both = [], [], []
#     cli_collect_members_diff(options, left.methods, right.methods,
#                              added, removed, both)

#     ret = NO_CHANGE

#     if not options.ignore_added and added:
#         print "Added methods:"
#         for l,r in added:
#             print "  ", r.pretty_descriptor()
#         ret = METHOD_DATA_CHANGE

#     if removed:
#         print "Removed methods:"
#         for l,r in removed:
#             print "  ", l.pretty_descriptor()
#         ret = METHOD_DATA_CHANGE

#     def print_changed(meth, changes, pc=[True]):
#         if pc[0]:
#             print "Changed methods:"
#             pc[0] = False

#         print "  ", meth.pretty_descriptor()
#         for change in changes:
#             print "    ", change

#     if both:
#         for l,r in both:
#             changes = cli_compare_method(options, l, r)
#             if changes:
#                 print_changed(r, changes)
#                 ret = METHOD_DATA_CHANGE

#     return ret



# def cli_compare_constants(options, left, right):

#     """ returns either NO_CHANGE or CONST_DATA_CHANGE, and prints out
#     a message to stdout """

#     if options.ignore_pool or left.consts == right.consts:
#         return NO_CHANGE

#     else:
#         print "Constant pool is altered."
#         return CONST_DATA_CHANGE



def options_magic(options):

    # turn a --ignore list into the individual ignore flags
    ign = (i.strip() for i in options.ignore.split(","))
    for i in (i.replace("-","_") for i in ign if i):
        setattr(options, "ignore_"+i, True)
    
    # lines or --ignore-lines is a shortcut for ignoring both absolute
    # and relative line number changes
    if options.ignore_lines:
        options.ignore_absolute_lines = True
        options.ignore_relative_lines = True

    if options.ignore_version:
        options.ignore_version_up = True
        options.ignore_version_down = True

    if options.ignore_platform:
        options.ignore_platform_up = True
        options.ignore_platform_down = True



# def old_cli_classes_info(options, left_i, right_i):

#     ret = NO_CHANGE
#     ret += cli_compare_class(options, left_i, right_i)
#     ret += cli_compare_fields(options, left_i, right_i)
#     ret += cli_compare_methods(options, left_i, right_i)
#     ret += cli_compare_constants(options, left_i, right_i)
    
#     return ret



def verbose_change(change, options, indent=0):
    indentstr = "  " * indent

    
    if change.is_change():
        if change.is_ignored(options):
            if options.show_ignored:
                print indentstr + change.get_description() + " [IGNORED]"
        else:
            print indentstr + change.get_description()
            
    elif options.show_unchanged:
        print indentstr + change.get_description()

    for sub in change.get_subchanges():
        verbose_change(sub, options, indent+1)



def cli_classes_diff(options, left, right):

    delta = JavaClassChange(left, right)
    delta.check()

    verbose_change(delta, options)

    if (not delta.is_change()) or delta.is_ignored(options):
        return 0
    else:
        return 1
    


def cli(options, rest):
    import javaclass

    #output_filter = WriteFilter(options.verbosity, sys.stdout)

    options_magic(options)

    left_f, right_f = rest[1:3]
    left_i = javaclass.unpack_classfile(left_f)
    right_i = javaclass.unpack_classfile(right_f)
    
    return cli_classes_diff(options, left_i, right_i)



def create_optparser():
    from optparse import OptionParser

    parse = OptionParser()

    #parse.add_option("--verbosity", action="store", type="int")
    #parse.add_option("-v", dest="verbosity", action="increment")

    parse.add_option("--show-ignored", action="store_true")
    parse.add_option("--show-unchanged", action="store_true")

    parse.add_option("--ignore", action="store", default="")
    parse.add_option("--ignore-version", action="store_true")
    parse.add_option("--ignore-version-up", action="store_true")
    parse.add_option("--ignore-version-down", action="store_true")
    parse.add_option("--ignore-platform", action="store_true")
    parse.add_option("--ignore-platform-up", action="store_true")
    parse.add_option("--ignore-platform-down", action="store_true")
    parse.add_option("--ignore-lines", action="store_true")
    parse.add_option("--ignore-absolute-lines", action="store_true")
    parse.add_option("--ignore-relative-lines", action="store_true")
    parse.add_option("--ignore-deprecated", action="store_true")
    parse.add_option("--ignore-added", action="store_true")
    parse.add_option("--ignore-pool", action="store_true")

    return parse
    


def main(args):
    parser = create_optparser()
    return cli(*parser.parse_args(args))



if __name__ == "__main__":
    sys.exit(main(sys.argv))



#
# The end.
