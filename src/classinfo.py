"""

Let's pretend to be the javap tool shipped with many Java SDKs

author: Christopher O'Brien  <obriencj@gmail.com>

"""



import sys



PUBLIC = 1
PACKAGE = 3
PRIVATE = 7



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
        print "  Signature:", field.get_descriptor()

    if options.verbose:
        cv = field.get_constantvalue()
        if cv is not None:
            t,v = field.owner.pretty_const_type_val(cv)
            if t:
                print "  Constant value: %s %s" % (t,v)
        print



def print_method(options, method):
    import javaclass.opcodes as opcodes

    if options.indent:
        print "   ",

    print "%s;" % method.pretty_descriptor()

    if options.sigs:
        print "  Signature:", method.get_descriptor()

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
        print "  LineNumberTable:"
        for (o,l) in method.get_code().get_linenumbertable():
            print "   line %i: %i" % (l,o)

    if options.locals and code:
        if method.owner:
            cval = method.owner.get_const_val
        else:
            cval = str

        lvt = method.get_code().get_localvariabletable()
        lvtt = method.get_code().get_localvariabletypetable()

        if lvt:
            print "  LocalVariableTable:"
            print "   Start\tLength\tSlot\tName\tDescriptor"
            for (o,l,n,d,i) in lvt:
                line = (str(o), str(l), str(i), cval(n), cval(d))
                print "   %s" % "\t".join(line)

        if lvtt:
            print "  LocalVariableTypeTable:"
            print "   Start\tLength\tSlot\tName\tSignature"
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



def print_class(options, classfile):
    from javaclass import unpack_classfile

    info = unpack_classfile(classfile)

    print "Compiled from \"%s\"" % info.get_sourcefile()
    print info.pretty_descriptor(),

    if options.verbose:
        print
        if info.get_sourcefile():
            print "  SourceFile: \"%s\"" % info.get_sourcefile()
        if info.get_signature():
            print "  Signature: %s" % info.get_signature()
        if info.get_enclosingmethod():
            print "  EnclosingMethod: %s" % info.get_enclosingmethod()
        print "  minor version: %i" % info.version[0]
        print "  major version: %i" % info.version[1]

    if options.constpool:
        print "  Constant pool:"
        for i in xrange(1, len(info.consts)):
            t,v = info.pretty_const_type_val(i)
            if t:
                # skipping the None consts, which would be the entries
                # comprising the second half of a long or double value
                print "const #%i = %s\t%s;" % (i,t,v)
        print
        
    print "{"

    for field in info.fields:
        if should_show(options, field):
            print_field(options, field)

    for method in info.methods:
        if should_show(options, method):
            print_method(options, method)

    print "}"
    print



def create_optparser():
    from optparse import OptionParser

    p = OptionParser("%prog <options> <classfiles>")

    p.add_option("--public", dest="show",
                 action="store_const", default=PUBLIC, const=PUBLIC,
                 help="show only public members")

    p.add_option("--private", dest="show",
                 action="store_const", const=PRIVATE,
                 help="show public and protected members")

    p.add_option("--package", dest="show",
                 action="store_const", const=PACKAGE,
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
        print_class(options, f)
        
    return 0



def main(args):
    parser = create_optparser()
    return cli(*parser.parse_args(args))



if __name__ == "__main__":
    sys.exit(main(sys.argv))



#
# The end.
