#!/usr/bin/env python2


"""

"""



import sys



PUBLIC = 1
PACKAGE = 3
PRIVATE = 7



def print_field(options, field):
    pass



def print_method(options, method):
    pass



def print_class(options, classfile):
    import javaclass

    info = javaclass.load_from_classfile(classfile)

    print "%s class %s%s%s{"

    for field in info.fields:
        print_field(options, field)

    for method in info.methods:
        print_method(options, method)

    print "}"



def create_optparser():
    from optparse import OptionParser

    p = OptionParser("%prog <options> <classfiles>")

    p.add_option("--public", dest="show", action="store", value=PUBLIC)
    p.add_option("--private", dest="show", action="store", value=PRIVATE)
    p.add_option("--package", dest="show", action="store", value=PACKAGE)

    p.add_option("-l", dest="lines", action="store_true")
    p.add_option("-c", dest="disassemble", action="store_true")
    p.add_option("-s", dest="sigs", action="store_true")
    p.add_option("--verbose", dest="verbose", action="store_true")
    
    return p



def cli(options, rest):
    return 0



def main(args):
    parser = create_optparser()
    return cli(*parser.parse_args(args))



if __name__ == "__main__":
    sys.exit(main(sys.argv))



#
# The end.
