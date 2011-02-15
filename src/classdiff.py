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
from change import yield_sorted_by_type



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



class ClassSignatureChange(GenericChange):
    label = "Generics Signature"


    def fn_data(self, c):
        return c.get_signature()



class ClassInfoChange(SuperChange):
    label = "Class information"

    change_types = (ClassNameChange,
                    ClassVersionChange,
                    ClassPlatformChange,
                    ClassSuperclassChange,
                    ClassInterfacesChange,
                    ClassAccessflagsChange,
                    ClassDeprecationChange,
                    ClassSignatureChange)



class MemberSuperChange(SuperChange):
    
    """ basis for FieldChange and MethodChange """
    
    label = "Member"


    def get_description(self):
        return "%s: %s" % (self.label, self.ldata.pretty_descriptor())



class MemberAdded(Change):
    
    """ basis for FieldAdded and MethodAdded """
    
    label = "Member added"


    def is_change(self):
        return True


    def get_description(self):
        return "%s: %s" % (self.label, self.rdata.pretty_descriptor())



class MemberRemoved(Change):
    
    """ basis for FieldChange and MethodChange """
    
    label = "Member removed"


    def is_change(self):
        return True


    def get_description(self):
        return "%s: %s" % (self.label, self.ldata.pretty_descriptor())



class ClassMembersChange(SuperChange):

    """ basis for ClassFieldsChange and ClassMethodsChange """
    
    label = "Members"

    member_added = MemberAdded
    member_removed = MemberRemoved
    member_changed = MemberSuperChange

    
    def collect_impl(self):
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
                largs[0] = left.cpool.deref_const(largs[0])
                rargs[0] = right.cpool.deref_const(rargs[0])

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
        


class MethodSignatureChange(GenericChange):
    label = "Method Generic Signature"


    def fn_data(self, c):
        return c.get_signature()



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
                    MethodSignatureChange,
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



class FieldSignatureChange(GenericChange):
    label = "Field Generic Signature"


    def fn_data(self, c):
        return c.get_signature()



class FieldAccessflagsChange(GenericChange):
    label = "Field accessflags"


    def fn_data(self, c):
        return c.access_flags


    def fn_pretty(self, c):
        return ",".join(c.pretty_access_flags())



class FieldConstvalueChange(GenericChange):
    label = "Field constvalue"


    def fn_data(self, c):
        return c.deref_constantvalue()



class FieldChange(MemberSuperChange):
    label = "Field"


    change_types = (FieldNameChange,
                    FieldTypeChange,
                    FieldSignatureChange,
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


    @yield_sorted_by_type(FieldAdded, FieldRemoved, FieldChange)
    def collect_impl(self):
        return super(ClassFieldsChange, self).collect_impl()

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


    @yield_sorted_by_type(MethodAdded, MethodRemoved, MethodChange)
    def collect_impl(self):
        return super(ClassMethodsChange, self).collect_impl()


    def __init__(self,lclass,rclass):
        ClassMembersChange.__init__(self,lclass.methods,rclass.methods)



class ClassConstantPoolChange(GenericChange):
    label = "Constant pool"


    def fn_data(self, c):
        return c.cpool.consts


    def is_ignored(self, options):
        return options.ignore_pool


    def get_description(self):
        return self.label + ((" unaltered", " altered")[self.is_change()])
        


class JavaClassChange(SuperChange):

    label = "Java Class"


    change_types = (ClassInfoChange,
                    ClassConstantPoolChange,
                    ClassFieldsChange,
                    ClassMethodsChange)


    def get_description(self):
        return "%s %s" % (self.label, self.ldata.pretty_descriptor())



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

    if options.verbose:
        options.show_unchanged = True
        options.show_ignored = True



def cli_classes_diff(options, left, right):
    options_magic(options)

    delta = JavaClassChange(left, right)
    delta.check()

    if not options.silent:
        delta.write(options)

    if (not delta.is_change()) or delta.is_ignored(options):
        return 0
    else:
        return 1
    


def cli(options, rest):
    from javaclass import unpack_classfile

    left = unpack_classfile(rest[1])
    right = unpack_classfile(rest[2])

    return cli_classes_diff(options, left, right)



def create_optparser():
    from optparse import OptionParser

    parse = OptionParser("%prog <options> <old_classfile> <new_classfile>")

    parse.add_option("-q", dest="silent", action="store_true")
    parse.add_option("-o", dest="output", action="store")

    parse.add_option("-v", dest="verbose", action="store_true")
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
