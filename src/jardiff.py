"""

Utility script and module for producing a set of changes in a JAR
file. Takes the same options as the classdiff script, and in fact uses
the classdiff script's code on each non-identical member in a pair of
JAR files.

author: Christopher O'Brien  <obriencj@gmail.com>

"""



import sys



from change import Change, GenericChange, SuperChange
from change import yield_sorted_by_type
from classdiff import JavaClassChange
from manifest import ManifestChange
from dirdelta import fnmatches



class JarTypeChange(GenericChange):
    # exploded vs. zipped and compression level

    def fn_data(self, c):
        return c.__class__.__name__
    


class JarContentChange(Change):
    # a file or directory changed between JARs

    label = "Jar Content Changed"
    
    def get_description(self):
        return "%s: %s" % (self.label, self.ldata)


    def is_change(self):
        return True


    def is_ignored(self, options):
        if options.ignore_patterns:
            return fnmatches(options.ignore_patterns, self.ldata)

        return False



class JarContentAdded(JarContentChange):
    # A file or directory was added to a JAR

    label = "Jar Content Added"


    def get_description(self):
        return "%s: %s" % (self.label, self.rdata)


    def is_ignored(self, options):
        if options.ignore_patterns:
            return fnmatches(options.ignore_patterns, self.rdata)

        # todo: check against ignored empty directories
        return False



class JarContentRemoved(JarContentChange):
    # A file or directory was removed from a JAR

    label = "Jar Content Removed"


    def is_ignored(self, options):
        if options.ignore_patterns:
            return fnmatches(options.ignore_patterns, self.ldata)

        # todo: check against ignored empty directories
        return False



class JarClassAdded(JarContentAdded):
    label = "Java Class Added"



class JarClassRemoved(JarContentRemoved):
    label = "Java Class Removed"



class JarClassChange(JavaClassChange, JarContentChange):
    label = "Java Class Changed"



class JarManifestChange(ManifestChange, JarContentChange):
    label = "Jar Manifest Changed"



class JarSignatureChange(JarContentChange):
    label = "Jar Signature Data Changed"



class JarSignatureAdded(JarContentAdded):
    label = "Jar Signature Added"



class JarSignatureRemoved(JarContentRemoved):
    label = "Jar Signature Removed"



class JarContentsChange(SuperChange):
    label = "JAR Contents"


    @yield_sorted_by_type(JarManifestChange,
                          JarSignatureAdded,
                          JarSignatureRemoved,
                          JarSignatureChange,
                          JarContentAdded,
                          JarContentRemoved,
                          JarContentChange,
                          JarClassAdded,
                          JarClassRemoved,
                          JarClassChange)
    def changes_impl(self):
        from zipdelta import compare_zips, LEFT, RIGHT, DIFF, SAME
        from javaclass import is_class, unpack_class
        from manifest import Manifest

        left, right = self.ldata, self.rdata

        for event,entry in compare_zips(self.ldata, self.rdata):
            if event == SAME:
                pass

            elif event == DIFF:
                lfd = left.open(entry)
                rfd = right.open(entry)

                delta = None

                if entry == "META-INF/MANIFEST.MF":
                    # special case to catch MANIFEST

                    lm, rm = Manifest(), Manifest()
                    lm.parse(lfd)
                    rm.parse(rfd)
                    delta = JarManifestChange(lm, rm)
                
                elif fnmatches(("*.RSA","*.DSA","*.SF"), entry):
                    # special case to catch signatures

                    delta = JarSignatureChange(entry, entry)

                else:
                    # try it as a java class, otherwise just call it a
                    # file and be done with it
                    
                    ljc = unpack_class(lfd)
                    rjc = unpack_class(rfd)
                    
                    if ljc and rjc:
                        delta = JarClassChange(ljc, rjc)
                    else:
                        delta = JarContentChange(entry, entry)

                lfd.close()
                rfd.close()
                yield delta

            elif event == LEFT:
                if fnmatches(("*.RSA","*.DSA","*.SF"), entry):
                    yield JarSignatureRemoved(entry, None)

                else:
                    fd = left.open(entry)
                    jc = unpack_class(fd)
                    fd.close()
                    if jc:
                        yield JarClassRemoved(jc, None)
                    else:
                        yield JarContentRemoved(entry, None) 
                
            elif event == RIGHT:
                if fnmatches(("*.RSA","*.DSA","*.SF"), entry):
                    yield JarSignatureAdded(None, entry)

                else:
                    fd = left.open(entry)
                    jc = unpack_class(fd)
                    fd.close()
                    if jc:
                        yield JarClassAdded(None, jc)
                    else:
                        yield JarContentAdded(None, entry)



class JarChange(SuperChange):
    label = "JAR"

    change_types = (JarTypeChange,
                    JarContentsChange)



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



def options_magic(options):
    from classdiff import options_magic
    return options_magic(options)



def cli_jars_diff(options, left, right):
    options_magic(options)

    delta = JarChange(left, right)
    delta.check()

    delta.write(options)

    if (not delta.is_change()) or delta.is_ignored(options):
        return 0
    else:
        return 1



def cli(options, rest):
    from zipdelta import ZipFile

    left, right = rest[1:3]
    return cli_jars_diff(options, ZipFile(left), ZipFile(right))



def create_optparser():
    from classdiff import create_optparser
    parser = create_optparser()

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
