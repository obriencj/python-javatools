"""

Utility script and module for producing a set of changes in a JAR
file. Takes the same options as the classdiff script, and in fact uses
the classdiff script's code on each non-identical member in a pair of
JAR files.

author: Christopher O'Brien  <obriencj@gmail.com>

"""



import sys



from change import Change, SuperChange
from classdiff import JavaClassChange



class JarTypeChange(Change):
    # exploded vs. zipped and compression level
    pass



class JarManifestChange(Change):
    # only the main section attributes
    pass



class JarSignatureChange(Change):
    # presence and name of signatures
    pass



class JarContentAdded(Change):
    # A file or directory was added to a JAR

    def is_change(self):
        return True


    def is_ignored(self, options):
        # todo: check against the ignored pattern
        # todo: check against ignored empty directories
        return False



class JarContentRemoved(Change):
    # A file or directory was removed from a JAR

    def is_change(self):
        return True


    def is_ignored(self, options):
        # todo: check against the ignored pattern
        # todo: check against ignored empty directories
        return False
    


class JarContentChange(Change):
    # a file or directory changed between JARs
    pass



class JarClassAdded(JarContentAdded):
    # file was added, and it was a java class
    pass



class JarClassRemoved(JarContentRemoved):
    # a file was removed, and it was a java class
    pass



class JarClassChange(JarContentChange, JavaClassChange):
    # a file was changed, and it was a java class
    pass



class JarContentsChange(SuperChange):
    label = "JAR Contents"


    def collect_impl(self):
        # run down the tree of left and right. Either may be a
        # directory or a zip file.
        pass


class JavaJarChange(SuperChange):
    label = "Java JAR"

    change_types = (JarTypeChange,
                    JarManifestChange,
                    JarCompressionChange,
                    JarSignatureChange,
                    JarContentsChange)



def fnmatches(pattern_list, entry):
    from fnmatch import fnmatch
    for pattern in pattern_list:
        if pattern and fnmatch(entry, pattern):
            return True
    return False



def cli_compare_jars(options, left, right):

    from classdiff import cli_classes_diff
    from zipfile import ZipFile
    from javaclass import is_class, unpack_class, JAVA_CLASS_MAGIC
    from zipdelta import compare_zips, LEFT, RIGHT, SAME, DIFF

    leftz, rightz = ZipFile(left, 'r'), ZipFile(right, 'r')

    for event,entry in compare_zips(leftz, rightz):
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
            # found a file that is in both JARs, but is not identical.
            # let's check if they are both class files, and if so, we
            # will attempt to discover a summary of changes.

            leftfd, rightfd = leftz.open(entry), rightz.open(entry)

            if is_class(leftfd) and is_class(rightfd):
                print "Changed class:", entry

                lefti = unpack_class(leftfd, magic=JAVA_CLASS_MAGIC)
                righti = unpack_class(rightfd, magic=JAVA_CLASS_MAGIC)
                cli_classes_diff(options, lefti, righti)

            else:
                print "Changed file:", entry
            
            leftfd.close()
            rightfd.close()



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
