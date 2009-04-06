"""

Utility script and module for producing a set of changes in a JAR
file. Takes the same options as the classdiff script, and in fact uses
the classdiff script's code on each non-identical member in a pair of
JAR files.

author: Christopher O'Brien  <siege@preoccupied.net>

"""



import sys



def cli_compare_jars(options, left, right):
    import javaclass, zipdelta, classdiff
    from zipfile import ZipFile

    from zipdelta import LEFT, RIGHT, BOTH, DIFF


    leftz, rightz = ZipFile(left, 'r'), ZipFile(right, 'r')

    for event,entry in zipdelta.compare_zips(leftz, rightz):
        if event == LEFT:
            print "Removed file:", entry

        elif event == RIGHT:
            print "Added file:", entry

        elif event == BOTH:
            # let's not bother to print the lack of a change, that's
            # just silly.

            pass

        elif event == DIFF:
            print "Changed file:", entry

            leftd, rightd = leftz.read(entry), rightz.read(entry)
            if javaclass.is_class(leftd) and javaclass.is_class(rightd):
                lefti = javaclass.unpack_class(leftd)
                righti = javaclass.unpack_class(rightd)
                classdiff.cli_classes_info(options, lefti, righti)

            else:
                pass

    # might want to make this do something more fun later
    return 0



def cli(options, rest):
    from classdiff import options_magic

    options_magic(options)
    left, right = rest[1:3]

    return cli_compare_jars(options, left, right)



def main(args):
    from classdiff import create_optparser

    parser = create_optparser()
    return cli(*parser.parse_args(args))



if __name__ == "__main__":
    sys.exit(main(sys.argv))



#
# The end.
