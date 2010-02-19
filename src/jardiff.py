"""

Utility script and module for producing a set of changes in a JAR
file. Takes the same options as the classdiff script, and in fact uses
the classdiff script's code on each non-identical member in a pair of
JAR files.

author: Christopher O'Brien  <obriencj@gmail.com>

"""



import sys



def fnmatches(pattern_list, entry):
    from fnmatch import fnmatch
    for pattern in pattern_list:
        if pattern and fnmatch(entry, pattern):
            return True
    return False



def cli_compare_jars(options, left, right):
    import javaclass, zipdelta
    from classdiff import cli_classes_info
    from zipfile import ZipFile

    from zipdelta import LEFT, RIGHT, SAME, DIFF

    leftz, rightz = ZipFile(left, 'r'), ZipFile(right, 'r')

    for event,entry in zipdelta.compare_zips(leftz, rightz):
        if fnmatches(options.ignore_content, entry):
            # ignoring this entry
            continue

        if event == LEFT:
            print "Removed file:", entry

        elif event == RIGHT:
            print "Added file:", entry

        elif event == SAME:
            # let's not bother to print the lack of a change, that's
            # just silly.

            pass

        elif event == DIFF:
            leftd, rightd = leftz.read(entry), rightz.read(entry)

            if javaclass.is_class(leftd) and javaclass.is_class(rightd):
                print "Changed class:", entry

                lefti = javaclass.unpack_class(leftd)
                righti = javaclass.unpack_class(rightd)
                cli_classes_info(options, lefti, righti)

            else:
                print "Changed file:", entry



def cli_compare_dirs(options, leftd, rightd):
    from dirdelta import compare, LEFT, RIGHT, SAME, DIFF
    from os.path import join

    for event,entry in compare(leftd, rightd):
        if not fnmatches(("*.jar","*.sar","*.ear","*.war"), entry):
            # skip non-JARs. This is a terrible way to test for this,
            # but I am in a hurry.
            continue

        if fnmatches(options.ignore_jar, entry):
            # skip
            continue
    
        elif event == LEFT:
            if options.ignore_jar_removed:
                continue
            else:
                print "JAR Removed:", entry
            
        elif event == RIGHT:
            if options.ignore_jar_added:
                continue
            else:
                print "JAR Added:", entry

        elif event == SAME:
            continue

        elif event == DIFF:
            print "JAR Changed:", entry
            cli_compare_jars(options, join(leftd, entry[len(rightd):]), entry)

        # print an empty line, for legibility
        print
            

def cli(options, rest):
    from classdiff import options_magic

    options_magic(options)
    left, right = rest[1:3]

    if options.recursive:
        return cli_compare_dirs(options, left, right)
    else:
        return cli_compare_jars(options, left, right)



def create_optparser():
    from classdiff import create_optparser
    parser = create_optparser()

    parser.add_option("-r", "--recursive", action="store_true")
    parser.add_option("--ignore-jar", action="append", default=[])
    parser.add_option("--ignore-content", action="append", default=[])
    parser.add_option("--ignore-jar-added", action="store_true")
    parser.add_option("--ignore-jar-removed", action="store_true")

    return parser



def main(args):
    parser = create_optparser()
    return cli(*parser.parse_args(args))



if __name__ == "__main__":
    sys.exit(main(sys.argv))



#
# The end.
