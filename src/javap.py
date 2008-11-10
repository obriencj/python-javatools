#!/usr/bin/env python2


"""

Let's pretend to be the javap tool shipped with many Java SDKs

author: Christopher O'Brien  <siege@preoccupied.net>

"""



import sys
import javaclass
import javaclass.opcodes as opcodes



PUBLIC = 1
PACKAGE = 3
PRIVATE = 7



def print_field(options, field):
    print "%s;" % field.pretty_descriptor()

    if options.sigs:
        print "  Signature:", field.get_descriptor()



def print_method(options, method):
    print "%s;" % method.pretty_descriptor()

    if options.sigs:
        print "  Signature:", method.get_descriptor()

    if options.disassemble:
        print "  Code:"
        for line in method.get_code().disassemble():
            opname = opcodes.get_opname_by_code(line[1])
            args = line[2]
            if args:
                args = ", ".join(map(str,args))
                print "   %i:\t%s\t%s" % (line[0], opname, args)
            else:
                print "   %i:\t%s" % (line[0], opname)

    if options.lines:
        if options.disassemble:
            print

        print "  LineNumberTable:"
        for (o,l) in method.get_code().get_linenumbertable():
            print "   line %i: %i" % (l,o)



def print_class(options, classfile):

    info = javaclass.unpack_classfile(classfile)

    print "Compiled from \"%s\"" % info.get_sourcefile()

    if options.constpool:
        print
        print "Constants Pool:"
        for i in xrange(1, len(info.consts)):
            c = info.pretty_const(i)
            if c:
                print c

    print
    print "class %s {" % info.pretty_name()

    for field in info.fields:
        print_field(options, field)
        print

    for method in info.methods:
        print_method(options, method)
        print

    print "}"



def create_optparser():
    from optparse import OptionParser

    p = OptionParser("%prog <options> <classfiles>")

    p.add_option("--public", dest="show", action="store_const", const=PUBLIC)
    p.add_option("--private", dest="show", action="store_const", const=PRIVATE)
    p.add_option("--package", dest="show", action="store_const", const=PACKAGE)

    p.add_option("-l", dest="lines", action="store_true")
    p.add_option("-c", dest="disassemble", action="store_true")
    p.add_option("-s", dest="sigs", action="store_true")
    p.add_option("-p", dest="constpool", action="store_true")
    p.add_option("--verbose", dest="verbose", action="store_true")
    
    return p



def cli(options, rest):
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
