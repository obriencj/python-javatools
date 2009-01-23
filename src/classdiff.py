#!/usr/bin/env python2


"""

"""



import sys



IDENTICAL_CLASS = 0
CLASS_DATA_CHANGE = 1 << 1
FIELD_DATA_CHANGE = 1 << 2
METHOD_DATA_CHANGE = 1 << 3
CONST_DATA_CHANGE = 1 << 4



LEFT = "left"
RIGHT = "right"
BOTH = "both"



def WriteFilter(object):
    def __init__(self, threshold, out):
        self.v = threshold
        self.o = out

    def write(self,level,*args):
        if level >= self.v:
            self.o.write(*args)

    def writelines(self,level,*args):
        if level >= self.v:
            self.o.writelines(*args)



def cli_compare_class(options, left, right):
    from javaclass import JavaClassInfo

    if not (isinstance(left, JavaClassInfo) and
            isinstance(right, JavaClassInfo)):
        raise TypeError("wanted JavaClassInfo")

    ret = 0

    # name
    if left.get_this() != right.get_this():
        print "Class name changed: %s to %s" % \
            (left.pretty_this(), right.pretty_this())
        ret = CLASS_DATA_CHANGE

    # sourcefile

    # version
    if not options.ignore_version and (left.version != right.version):
        print "Java version changed: %r to %r" % \
            (left.version, right.version)
        ret = CLASS_DATA_CHANGE

    # inheritance
    if left.get_super() != right.get_super():
        print "Superclass changed: %s to %s" % \
            (left.pretty_super(), right.pretty_super())

    # interfaces
    li, ri = set(left.get_interfaces()), set(right.get_interfaces())
    if li != ri:
        print "Interfaces changed: (%s) to (%s)" % \
            (", ".join(li), ", ".join(ri))
        ret = CLASS_DATA_CHANGE

    # access flags
    if left.access_flags != right.access_flags:
        print "Access flags changed: %s to %s" % \
            (left.pretty_access_flags(), right.pretty_access_flags())
        ret = CLASS_DATA_CHANGE

    # deprecation
    if not options.ignore_deprecated and \
            (left.is_deprecated() != right.is_deprecated()):
        print "Deprecation became %s" % right.is_deprecated()
        ret = CLASS_DATA_CHANGE

    return ret



def cli_members_diff(options, left_members, right_members):
    
    """ generator yielding (EVENT, (left_meth, right_meth)) """

    li = {}
    for f in left_members:
        li[f.get_identifier()] = f

    for f in right_members:
        key = f.get_identifier()
        lf = li.get(key, None)

        if lf:
            del li[key]
            yield (BOTH, (lf, f))
        else:
            yield (RIGHT, (None, f))
    
    for f in li.values():
        yield (LEFT, (f, None))
        


def cli_collect_members_diff(options, left_members, right_members,
                             added=None, removed=None, both=None):
    
    for event,data in cli_members_diff(options, left_members, right_members):
        l = None

        if event is LEFT:
            l = removed
        elif event is RIGHT:
            l = added
        elif event is BOTH:
            l = both
        
        if l is not None:
            l.append(data)

    return added, removed, both



def _cli_compare_field(options, left, right):
    
    from javaclass import JavaMemberInfo
    
    if not (isinstance(left, JavaMemberInfo) and
            isinstance(right, JavaMemberInfo)):
        raise TypeError("wanted JavaMemberInfo")
    
    if left.get_name() != right.get_name():
        yield "name changed from %s to %s" % \
            (left.get_name(), right.get_name())
        
    if left.get_descriptor() != right.get_descriptor():
        yield "type changed from %s to %s" % \
            (left.pretty_type(), right.pretty_type())

    if left.access_flags != right.access_flags:
        yield "access flags changed from (%s) to (%s)" % \
            (",".join(left.pretty_access_flags()),
             ",".join(right.pretty_access_flags()))
        
    if left.get_const_val() != right.get_const_val():
        yield "constant value changed"



def cli_compare_field(options, left, right):
    return [change for change in _cli_compare_field(options, left, right)]



def cli_compare_fields(options, left, right):

    added, removed, both = [], [], []

    cli_collect_members_diff(options, left.fields, right.fields,
                             added, removed, both)

    ret = 0

    if not options.ignore_added and added:
        print "Added fields:"
        for l,r in added:
            print "  ", r.pretty_descriptor()
        ret = FIELD_DATA_CHANGE

    if removed:
        print "Removed fields:"
        for l,r in removed:
            print "  ", l.pretty_descriptor()
        ret = FIELD_DATA_CHANGE

    def print_changed(field, changes):
        if print_changed.p:
            print "Changed fields:"
            print_changed.p = False

        print "  ", field.pretty_descriptor()
        for change in changes:
            print "    ", change
    print_changed.p = True

    if both:
        for l,r in both:
            changes = cli_compare_field(options, l, r)
            if changes:
                print_changed(r, changes)
                ret = FIELD_DATA_CHANGE

    return ret



def relative_lnt(lnt):
    lineoff = lnt[0][1]
    return [(o,l-lineoff) for (o,l) in lnt]



def _cli_compare_code(options, left, right):

    from javaclass import JavaCodeInfo
    import javaclass.opcodes as opcodes

    if not (isinstance(left, JavaCodeInfo) and
            isinstance(right, JavaCodeInfo)):
        raise TypeError("wanted JavaCodeInfo")

    l_lnt, r_lnt = left.get_linenumbertable(), right.get_linenumbertable()
    if (not options.ignore_absolute_lines and l_lnt != r_lnt):
        yield "absolute line numbers changed"

    l_lnt, r_lnt = relative_lnt(l_lnt), relative_lnt(r_lnt)
    if (not options.ignore_relative_lines and l_lnt != r_lnt):
        yield "relative line numbers changed"

    if left.max_stack != right.max_stack:
        yield "max stack size changed from %i to %i" % \
            (left.max_stack, right.max_stack)

    if left.max_locals != right.max_locals:
        yield "max locals changed from %i to %i" % \
            (left.max_locals, right.max_locals)

    if left.exceptions != right.exceptions:
        yield "exception table changed"

    if len(left.code) == len(right.code):
        code_vals_change = False
        code_body_change = False

        for l,r in zip(left.disassemble(), right.disassemble()):
            if not ((l[0] == r[0]) and (l[1] == r[1])):
                code_body_change = True
                break

            largs, rargs = l[2], r[2]

            if opcodes.has_const_arg(l[1]):
                largs, rargs = list(largs), list(rargs)
                largs[0] = left.owner.get_const_val(largs[0])
                rargs[0] = right.owner.get_const_val(rargs[0])

            if largs != rargs:
                code_vals_change = True
                break

        if code_vals_change:
            yield "code constants changed"

    else:
        print "length changed:", len(left.code), len(right.code)
        code_body_change = True

    if code_body_change:
        yield "code body changed"



def cli_compare_code(options, left, right):
    return [change for change in _cli_compare_code(options, left, right)]



def _cli_compare_method(options, left, right):

    from javaclass import JavaMemberInfo

    if not (isinstance(left, JavaMemberInfo) and
            isinstance(right, JavaMemberInfo)):
        raise TypeError("wanted JavaMemberInfo")

    if left.get_name() != right.get_name():
        yield "name changed from %s to %s" % \
            (left.get_name(), right.get_name())

    if left.get_type_descriptor() != right.get_type_descriptor():
        yield "return type changed from %s to %s" % \
            (left.pretty_type(), right.pretty_type())

    if left.get_arg_type_descriptors() != right.get_arg_type_descriptors():
        yield "parameters changed from (%s) to (%s)" % \
            (",".join(left.pretty_arg_types()),
             ",".join(right.pretty_arg_types()))

    if left.access_flags != right.access_flags:
        yield "access flags changed from (%s) to (%s)" % \
            (",".join(left.pretty_access_flags()),
             ",".join(right.pretty_access_flags()))

    if set(left.get_exceptions()) != set(right.get_exceptions()):
        yield "exceptions changed from (%s) to (%s)" % \
            (",".join(left.pretty_exceptions()),
             ",".join(right.pretty_exceptions()))

    for c in _cli_compare_code(options, left.get_code(), right.get_code()):
        yield c
        


def cli_compare_method(options, left, right):
    return [change for change in _cli_compare_method(options, left, right)]



def cli_compare_methods(options, left, right):
    
    added, removed, both = [], [], []
    cli_collect_members_diff(options, left.methods, right.methods,
                             added, removed, both)

    ret = 0

    if not options.ignore_added and added:
        print "Added methods:"
        for l,r in added:
            print "  ", r.pretty_descriptor()
        ret = METHOD_DATA_CHANGE

    if removed:
        print "Removed methods:"
        for l,r in removed:
            print "  ", l.pretty_descriptor()
        ret = METHOD_DATA_CHANGE

    def print_changed(meth, changes):
        if print_changed.p:
            print "Changed methods:"
            print_changed.p = False

        print "  ", meth.pretty_descriptor()
        for change in changes:
            print "    ", change
    print_changed.p = True

    if both:
        for l,r in both:
            changes = cli_compare_method(options, l, r)
            if changes:
                print_changed(r, changes)
                ret = METHOD_DATA_CHANGE

    return ret



def cli_compare_constants(options, left, right):

    if options.ignore_pool or left.consts == right.consts:
        return 0

    else:
        print "Constant pool is altered."
        return 1



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



def cli(options, rest):
    import javaclass

    #output_filter = WriteFilter(options.verbosity, sys.stdout)

    options_magic(options)

    left_f, right_f = rest[1:3]
    left_i = javaclass.unpack_classfile(left_f)
    right_i = javaclass.unpack_classfile(right_f)

    ret = 0
    ret += cli_compare_class(options, left_i, right_i)
    ret += cli_compare_fields(options, left_i, right_i)
    ret += cli_compare_methods(options, left_i, right_i)
    ret += cli_compare_constants(options, left_i, right_i)
    
    return ret
    


def create_optparser():
    from optparse import OptionParser

    parse = OptionParser()

    parse.add_option("--verbosity", action="store", type="int")
    #parse.add_option("-v", dest="verbosity", action="increment")

    parse.add_option("--ignore", action="store", default="")
    parse.add_option("--ignore-version", action="store_true")
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
