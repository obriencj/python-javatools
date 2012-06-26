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
Utility script for comparing the internals of two Java class files for
differences in structure and data. Has options to specify changes
which may be immaterial or unimportant, such as re-ordering of the
constant pool, line number changes (either absolute or relative),
added fields or methods, deprecation changes, etc.

author: Christopher O'Brien  <obriencj@gmail.com>
license: LGPL
"""



from .change import GenericChange, SuperChange
from .change import Addition, Removal
from .change import yield_sorted_by_type



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

    def fn_pretty(self, c):
        return tuple(c.pretty_interfaces())



class ClassAccessflagsChange(GenericChange):
    label = "Access flags"


    def fn_data(self, c):
        return c.access_flags


    def fn_pretty(self, c):
        return tuple(c.pretty_access_flags())



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



class MemberAdded(Addition):
    
    """ basis for FieldAdded and MethodAdded """
    
    label = "Member added"


    def get_description(self):
        return "%s: %s" % (self.label, self.rdata.pretty_descriptor())



class MemberRemoved(Removal):
    
    """ basis for FieldChange and MethodChange """
    
    label = "Member removed"


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


    
class CodeAbsoluteLinesChange(GenericChange):
    label = "Absolute line numbers"


    def fn_data(self, c):
        return c.get_linenumbertable()


    def is_ignored(self, options):
        return options.ignore_absolute_lines
    


class CodeRelativeLinesChange(GenericChange):
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


    def fn_pretty(self, c):
        a = list()
        for e in c.exceptions:
            p = (e.start_pc, e.end_pc, e.handler_pc, e.pretty_catch_type())
            a.append(p)
        return repr(a)



class CodeConstantsChange(GenericChange):

    """ This is a test to find instances where the individual opcodes
    and arguments for a method's code may all be identical except
    that ops which load from the constant pool may use a different
    index. We will deref the constant index for both sides, and if all
    of the constant values match then we can consider the code to be
    equal.

    The purpose of such a check is to find other-wise meaningless
    constant pool reordering. If all uses of the pool result in the
    same values, we don't really care if the pool is in a different
    order between the old and new versions of a class.
    """


    label = "Code constants"


    def __init__(self, l, r):
        GenericChange.__init__(self, l, r)
        self.offsets = None


    def fn_pretty(self, c):
        from javatools import opcodes
        
        if not self.offsets:
            return None

        pr = list()

        for offset,code,args in c.disassemble():
            if offset in self.offsets and opcodes.has_const_arg(code):
                name = opcodes.get_opname_by_code(code)
                data = c.cpool.pretty_deref_const(args[0])
                pr.append((offset, name, data))
                
        return pr


    def check_impl(self):
        from javatools import opcodes
        from itertools import izip
        
        left,right = self.ldata, self.rdata
        offsets = list()

        if len(left.code) != len(right.code):
            # code body change, can't determine constants
            return True, None
        
        for l,r in izip(left.disassemble(), right.disassemble()):
            if not ((l[0] == r[0]) and (l[1] == r[1])):
                # code body change, can't determine constants
                return True, None
            
            largs,rargs = l[2], r[2]
            if opcodes.has_const_arg(l[1]):
                largs, rargs = list(largs), list(rargs)
                largs[0] = left.cpool.deref_const(largs[0])
                rargs[0] = right.cpool.deref_const(rargs[0])

            if largs != rargs:
                offsets.append(l[0])

        self.offsets = offsets
        return bool(self.offsets), None
        


class CodeBodyChange(GenericChange):

    """ The length or the opcodes or the arguments of the opcodes has
    changed, signalling that the method body is different """

    label = "Code body"


    def fn_data(self, c):
        return c.disassemble()


    def fn_pretty(self, c):
        from javatools import opcodes
        
        pr = list()
        for offset,code,args in c.disassemble():
            name = opcodes.get_opname_by_code(code)
            pr.append((offset, name, args))
            
        return pr
    

    def check_impl(self):
        from itertools import izip

        left,right = self.ldata,self.rdata
                
        if len(left.code) != len(right.code):
            desc = "Code length changed from %r to %r" % \
                   (len(left.code), len(right.code))
            return True, desc

        for l,r in izip(left.disassemble(), right.disassemble()):
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
        return tuple(c.pretty_arg_types())

    

class MethodAccessflagsChange(GenericChange):
    label = "Method accessflags"


    def fn_data(self, c):
        return c.access_flags


    def fn_pretty(self, c):
        return tuple(c.pretty_access_flags())



class MethodAbstractChange(GenericChange):

    label = "Method abstract"


    def fn_data(self, c):
        return (not c.get_code())


    def fn_pretty_desc(self, c):
        if self.fn_data(c):
            return "Method is abstract"
        else:
            return "Method is concrete"



class MethodExceptionsChange(GenericChange):
    label = "Method exceptions"


    def fn_data(self, c):
        return c.get_exceptions()


    def fn_pretty(self, c):
        return tuple(c.pretty_exceptions())
        


class MethodCodeChange(SuperChange):
    label = "Method code"


    change_types = (CodeAbsoluteLinesChange,
                    CodeRelativeLinesChange,
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
        return tuple(c.pretty_access_flags())


    def fn_pretty_desc(self, c):
        return ",".join(c.pretty_access_flags())



class FieldConstvalueChange(GenericChange):
    label = "Field constvalue"


    def fn_data(self, c):
        return c.deref_constantvalue()


    def fn_pretty(self, c):
        return repr(c.deref_constantvalue())



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
        return ClassMembersChange.collect_impl(self)


    def __init__(self,lclass,rclass):
        ClassMembersChange.__init__(self,lclass.methods,rclass.methods)



class ClassConstantPoolChange(GenericChange):
    label = "Constant pool"


    def fn_data(self, c):
        return c.cpool.consts


    def fn_pretty(self, c):
        return tuple(c.cpool.pretty_constants())


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
        return "%s %s" % (self.label, self.ldata.pretty_this())



class JavaClassReport(JavaClassChange):
    

    def __init__(self, l, r, reporter):
        JavaClassChange.__init__(self, l, r)
        self.reporter = reporter


    def check(self):
        JavaClassChange.check(self)
        self.reporter.run(self)



# ---- Begin classdiff CLI code ----
#



def cli_classes_diff(parser, options, left, right):
    from .report import quick_report, Reporter
    from .report import JSONReportFormat, TextReportFormat
    from .report import CheetahReportFormat

    reports = getattr(options, "reports", tuple())
    if reports:
        rdir = options.report_dir or "./"
        rpt = Reporter(rdir, "JavaClassReport", options)

        for fmt in reports:
            if  fmt == "json":
                rpt.add_report_format(JSONReportFormat)
            elif fmt in ("txt", "text"):
                rpt.add_report_format(TextReportFormat)
            elif fmt in ("htm", "html"):
                rpt.add_report_format(CheetahReportFormat)
            else:
                parser.error("unknown report format: %s" % fmt)

        delta = JavaClassReport(left, right, rpt)

    else:
        delta = JavaClassChange(left, right)

    delta.check()

    if not options.silent:
        if options.json:
            quick_report(JSONReportFormat, delta, options)
        else:
            quick_report(TextReportFormat, delta, options)

    if (not delta.is_change()) or delta.is_ignored(options):
        return 0
    else:
        return 1



def cli(parser, options, rest):
    from javatools import unpack_classfile
    
    if len(rest) != 3:
        parser.error("wrong number of arguments.")

    left = unpack_classfile(rest[1])
    right = unpack_classfile(rest[2])

    return cli_classes_diff(parser, options, left, right)



def classdiff_optgroup(parser):
    from optparse import OptionGroup

    g = OptionGroup(parser, "Class Checking Options")

    g.add_option("--ignore-version-up", action="store_true", default=False)
    g.add_option("--ignore-version-down", action="store_true", default=False)
    g.add_option("--ignore-platform-up", action="store_true", default=False)
    g.add_option("--ignore-platform-down", action="store_true", default=False)
    g.add_option("--ignore-absolute-lines", action="store_true", default=False)
    g.add_option("--ignore-relative-lines", action="store_true", default=False)
    g.add_option("--ignore-deprecated", action="store_true", default=False)
    g.add_option("--ignore-added", action="store_true", default=False)
    g.add_option("--ignore-pool", action="store_true", default=False)

    g.add_option("--ignore-lines",
                 help="ignore relative and absolute line-number changes",
                 action="callback", callback=_opt_cb_ign_lines)

    g.add_option("--ignore-platform",
                 help="ignore platform changes",
                 action="callback", callback=_opt_cb_ign_platform)

    g.add_option("--ignore-version",
                 help="ignore version changes",
                 action="callback", callback=_opt_cb_ign_version)

    return g



def _opt_cb_ignore(opt, opt_str, value, parser):
    options = parser.values
    options.ignore = value

    if not value:
        return

    ign = (i.strip() for i in value.split(","))
    for i in (i for i in ign if i):
        iopt_str = "--ignore-"+i.replace("_","-")
        iopt = parser.get_option(iopt_str)
        if iopt:
            iopt.process(opt_str, value, options, parser)


def _opt_cb_ign_lines(opt, opt_str, value, parser):
    options = parser.values
    options.ignore_lines = True
    options.ignore_absolute_lines = True
    options.ignore_relative_lines = True


def _opt_cb_ign_version(opt, opt_str, value, parser):
    options = parser.values
    options.ignore_version = True
    options.ignore_version_up = True
    options.ignore_version_down = True


def _opt_cb_ign_platform(opt, opt_str, value, parser):
    options = parser.values
    options.ignore_platform = True
    options.ignore_platform_up = True
    options.ignore_platform_down = True


def _opt_cb_verbose(opt, opt_str, value, parser):
    options = parser.values
    options.verbose = True
    options.show_unchanged = True
    options.show_ignored = True



def general_optgroup(parser):
    from optparse import OptionGroup

    g = OptionGroup(parser, "General Options")

    g.add_option("-q", "--quiet", dest="silent",
                 action="store_true", default=False)
    
    g.add_option("-v", "--verbose",
                 action="callback", callback=_opt_cb_verbose)
    
    g.add_option("-o", "--output", dest="output",
                 action="store", default=None)
    
    g.add_option("-j", "--json", dest="json",
                 action="store_true", default=False)
    
    g.add_option("--show-ignored", action="store_true", default=False)
    g.add_option("--show-unchanged", action="store_true", default=False)
    
    g.add_option("--ignore", action="callback", type="string",
                 help="comma-separated list of ignores",
                 callback=_opt_cb_ignore)

    return g



def create_optparser():
    from optparse import OptionParser
    from javatools import report

    parser = OptionParser("%prog [OPTIONS] OLD_CLASS NEW_CLASS")

    parser.add_option_group(general_optgroup(parser))
    parser.add_option_group(classdiff_optgroup(parser))

    parser.add_option_group(report.general_report_optgroup(parser))
    parser.add_option_group(report.json_report_optgroup(parser))
    parser.add_option_group(report.html_report_optgroup(parser))

    return parser
    


def main(args):
    parser = create_optparser()
    return cli(parser, *parser.parse_args(args))



#
# The end.
