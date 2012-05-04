"""

Let's pretend to be the javap tool shipped with many Java SDKs

author: Christopher O'Brien  <obriencj@gmail.com>

"""



import sys



HEADER = 0
PUBLIC = 1
PACKAGE = 3
PRIVATE = 7



def get_class_info_requires(info):
    from javaclass import CONST_Class

    deps = []
    for t,v in info.pretty_constants():
        if t is CONST_Class:
            deps.append(v)
    return set(deps)



def should_show(options, member):

    """ whether to show a member by its access flags and the show
    option. There's probably a faster and smarter way to do this, but
    eh. """

    show = options.show
    if show == PUBLIC:
        return member.is_public()
    elif show == PACKAGE:
        return member.is_public() or member.is_protected()
    elif show == PRIVATE:
        return True



def print_field(options, field):

    if options.indent:
        print "   ",

    print "%s;" % field.pretty_descriptor()

    if options.sigs:
        print "  Signature:", field.get_signature()

    if options.verbose:
        cv = field.get_constantvalue()
        if cv is not None:
            t,v = field.cpool.pretty_const(cv)
            if t:
                print "  Constant value:", t, v
        print



def print_method(options, method):
    import javaclass.opcodes as opcodes

    if options.indent:
        print "   ",

    print "%s;" % method.pretty_descriptor()

    if options.sigs:
        print "  Signature:", method.get_signature()

    code = method.get_code()
    if options.disassemble and code:

        print "  Code:"

        if options.verbose:
            # the arg count is the number of arguments consumed from
            # the stack when this method is called. non-static methods
            # implicitly have a "this" argument that's not in the
            # descriptor
            argsc = len(method.get_arg_type_descriptors())
            if not method.is_static():
                argsc += 1

            print "   Stack=%i, Locals=%i, Args_size=%i" % \
                (code.max_stack, code.max_locals, argsc)

        for line in code.disassemble():
            opname = opcodes.get_opname_by_code(line[1])
            args = line[2]
            if args:
                args = ", ".join(map(str,args))
                print "   %i:\t%s\t%s" % (line[0], opname, args)
            else:
                print "   %i:\t%s" % (line[0], opname)

        exps = code.exceptions
        if exps:
            print "  Exception table:"
            print "   from\tto\ttarget\ttype"
            for e in exps:
                ctype = e.pretty_catch_type()
                print "  % 4i\t% 4i\t% 4i\t%s" % \
                    (e.start_pc, e.end_pc, e.handler_pc, ctype)

    if options.verbose:
        if method.is_deprecated():
            print "  Deprecated: true"

        if method.is_synthetic():
            print "  Synthetic: true"

        if method.is_bridge():
            print "  Bridge: true"

        if method.is_varargs():
            print "  Varargs: true"

    if options.lines and code:
        lnt = method.get_code().get_linenumbertable()
        if lnt:
            print "  LineNumberTable:"
            for (o,l) in lnt:
                print "   line %i: %i" % (l,o)

    if options.locals and code:
        if method.cpool:
            cval = method.cpool.deref_const
        else:
            cval = str

        lvt = method.get_code().get_localvariabletable()
        lvtt = method.get_code().get_localvariabletypetable()

        if lvt:
            print "  LocalVariableTable:"
            print "   Start  Length  Slot\tName\tDescriptor"
            for (o,l,n,d,i) in lvt:
                line = (str(o), str(l), str(i), cval(n), cval(d))
                print "   %s" % "\t".join(line)

        if lvtt:
            print "  LocalVariableTypeTable:"
            print "   Start  Length  Slot\tName\tSignature"
            for (o,l,n,s,i) in lvtt:
                line = (str(o), str(l), str(i), cval(n), cval(s))
                print "   %s" % "\t".join(line)


    if options.verbose:
        exps = method.pretty_exceptions()
        if exps:
            print "  Exceptions:"
            for e in exps:
                print "   throws", e

        print



def cli_api_provides(options, info):
    print "class %s provides:" % info.pretty_this()

    provides = list(info.get_provides())
    provides.sort()

    for provided in provides:
        print " ", provided
    print



def cli_api_requires(options, info):
    print "class %s requires:" % info.pretty_this()

    requires = list(info.get_requires())
    requires.sort()

    for required in requires:
        print " ", required
    print



def cli_print_classinfo(options, info):
    from javaclass import platform_from_version

    if options.api_requires or options.api_provides:
        if options.api_provides:
            cli_api_provides(options, info)

        if options.api_requires:
            cli_api_requires(options, info)

        return

    sourcefile = info.get_sourcefile()
    if sourcefile:
        print "Compiled from \"%s\"" % sourcefile

    print info.pretty_descriptor(),

    if options.verbose or options.show == HEADER:
        print
        if info.get_sourcefile():
            print "  SourceFile: \"%s\"" % info.get_sourcefile()
        if info.get_signature():
            print "  Signature:", info.get_signature()
        if info.get_enclosingmethod():
            print "  EnclosingMethod:", info.get_enclosingmethod()
        print "  minor version:", info.get_minor_version()
        print "  major version:", info.get_major_version()
        platform = platform_from_version(*info.version) or "unknown"
        print "  Platform:", platform

    if options.constpool:
        print "  Constant pool:"

        # we don't use the info.pretty_constants() generator here
        # because we actually want numbers for the entries, and that
        # generator skips them.
        cpool = info.cpool

        for i in xrange(1, len(cpool.consts)):
            t,v = cpool.pretty_const(i)
            if t:
                # skipping the None consts, which would be the entries
                # comprising the second half of a long or double value
                print "const #%i = %s\t%s;" % (i,t,v)
        print
        
    if options.show == HEADER:
        return

    print "{"

    for field in info.fields:
        if should_show(options, field):
            print_field(options, field)

    for method in info.methods:
        if should_show(options, method):
            print_method(options, method)

    print "}"
    print

    return 0



def cli_print_class(options, classfile):
    from javaclass import unpack_classfile

    info = unpack_classfile(classfile)
    return cli_print_classinfo(options, info)



def create_optparser():
    from optparse import OptionParser

    p = OptionParser("%prog <options> <classfiles>")

    p.add_option("--api-provides", dest="api_provides",
                 action="store_true", default=False,
                 help="Print only provided API information")
    
    p.add_option("--api-requires", dest="api_requires",
                 action="store_true", default=False,
                 help="Print only requires API information")

    p.add_option("--header", dest="show",
                 action="store_const", default=PUBLIC, const=HEADER,
                 help="show just the class header, no members")

    p.add_option("--public", dest="show",
                 action="store_const", const=PUBLIC,
                 help="show only public members")

    p.add_option("--package", dest="show",
                 action="store_const", const=PACKAGE,
                 help="show public and protected members")

    p.add_option("--private", dest="show",
                 action="store_const", const=PRIVATE,
                 help="show all members")

    p.add_option("-l", dest="lines", action="store_true",
                 help="show the line number table")

    p.add_option("-o", dest="locals", action="store_true",
                 help="show the local variable tables")

    p.add_option("-c", dest="disassemble", action="store_true",
                 help="disassemble method code")

    p.add_option("-s", dest="sigs", action="store_true",
                 help="show internal type signatures")

    p.add_option("-p", dest="constpool", action="store_true",
                 help="show the constants pool")

    p.add_option("--verbose", dest="verbose", action="store_true",
                 help="sets -locsp options and shows stack bounds")
    
    return p



def cli(options, rest):

    if options.verbose:
        # verbose also sets all of the following options
        options.lines = True
        options.locals = True
        options.disassemble = True
        options.sigs = True
        options.constpool = True

    # just a tiny hack to mimic some indenting sun's javap will do if
    # the output is terse
    options.indent = not(options.lines or
                         options.disassemble or
                         options.sigs)

    for f in rest[1:]:
        cli_print_class(options, f)
        
    return 0



def main(args):
    parser = create_optparser()
    return cli(*parser.parse_args(args))



if __name__ == "__main__":
    sys.exit(main(sys.argv))



#
# The end.
