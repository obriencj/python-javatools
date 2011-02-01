"""

Utility script and module for producing a set of changes in a JAR
file. Takes the same options as the classdiff script, and in fact uses
the classdiff script's code on each non-identical member in a pair of
JAR files.

author: Christopher O'Brien  <obriencj@gmail.com>

"""



import sys



from change import Change, GenericChange, SuperChange, Addition, Removal
from change import yield_sorted_by_type
from classdiff import JavaClassChange
from manifest import ManifestChange
from dirdelta import fnmatches



class JarTypeChange(GenericChange):
    # exploded vs. zipped and compression level

    label = "Jar type"

    def fn_data(self, c):
        return c.__class__.__name__
    


class JarContentChange(Change):
    # a file or directory changed between JARs

    label = "Jar Content Changed"
    

    def __init__(self, lzip, rzip, entry):
        Change.__init__(self, lzip, rzip)
        self.entry = entry


    def get_description(self):
        return "%s: %s" % (self.label, self.entry)


    def is_change(self):
        return True


    def is_ignored(self, options):
        return fnmatches(self.entry, *options.ignore_content)

        return False



class JarContentAdded(JarContentChange, Addition):
    # A file or directory was added to a JAR

    label = "Jar Content Added"


    def is_ignored(self, options):
        return fnmatches(self.entry, *options.ignore_content)

        # todo: check against ignored empty directories
        return False



class JarContentRemoved(JarContentChange, Removal):
    # A file or directory was removed from a JAR

    label = "Jar Content Removed"


    def is_ignored(self, options):
        return fnmatches(self.entry, *options.ignore_content)

        # todo: check against ignored empty directories
        return False



class JarClassAdded(JarContentAdded):
    label = "Java Class Added"



class JarClassRemoved(JarContentRemoved):
    label = "Java Class Removed"



class JarClassChange(SuperChange, JarContentChange):
    label = "Java Class Changed"

    
    def __init__(self, ldata, rdata, entry):
        JarContentChange.__init__(self, ldata, rdata, entry)


    def collect_impl(self):
        from javaclass import unpack_class
        lfd = self.ldata.open(self.entry)
        rfd = self.rdata.open(self.entry)
        
        linfo = unpack_class(lfd)
        rinfo = unpack_class(rfd)

        lfd.close()
        rfd.close()

        yield JavaClassChange(linfo, rinfo)



class JarManifestChange(SuperChange, JarContentChange):
    label = "Jar Manifest Changed"

    
    def __init__(self, ldata, rdata, entry):
        JarContentChange.__init__(self, ldata, rdata, entry)


    def collect_impl(self):
        from manifest import Manifest
        
        lfd = self.ldata.open(self.entry)
        rfd = self.rdata.open(self.entry)
        
        lm, rm = Manifest(), Manifest()
        lm.parse(lfd)
        rm.parse(rfd)

        lfd.close()
        rfd.close()

        yield ManifestChange(lm, rm)



class JarSignatureChange(JarContentChange):
    label = "Jar Signature Data Changed"

    def is_ignored(self, options):
        return True



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
    def collect_impl(self):
        from zipdelta import compare_zips, LEFT, RIGHT, DIFF, SAME

        left, right = self.ldata, self.rdata

        for event,entry in compare_zips(self.ldata, self.rdata):
            print event, entry
            
            if event == SAME:
                pass

            elif event == DIFF:
                if entry == "META-INF/MANIFEST.MF":
                    yield JarManifestChange(left, right, entry)
                
                elif fnmatches(entry, "*.RSA", "*.DSA", "*.SF"):
                    yield JarSignatureChange(left, right, entry)

                elif fnmatches(entry, "*.class"):
                    yield JarClassChange(left, right, entry)
                    
                else:
                    yield JarContentChange(left, right, entry)

            elif event == LEFT:
                if fnmatches(entry, "*.RSA", "*.DSA", "*.SF"):
                    yield JarSignatureRemoved(left, right, entry)

                elif fnmatches(entry, "*.class"):
                    yield JarClassRemoved(left, right, entry)

                else:
                    yield JarContentRemoved(left, right, entry) 
                
            elif event == RIGHT:
                if fnmatches(entry, "*.RSA","*.DSA","*.SF"):
                    yield JarSignatureAdded(left, right, entry)

                elif fnmatches(entry, "*.class"):
                    yield JarClassAdded(left, right, entry)

                else:
                    yield JarContentAdded(left, right, entry)



class JarChange(SuperChange):
    label = "JAR"

    change_types = (JarTypeChange,
                    JarContentsChange)


    def check(self):
        #print "entering JarChange.check()"
        SuperChange.check(self)
        self.ldata.close()
        self.rdata.close()
        #print "leaving JarChange.check()"



def options_magic(options):
    from classdiff import options_magic
    return options_magic(options)



def cli_jars_diff(options, left, right):
    options_magic(options)

    delta = JarChange(left, right)
    delta.check()

    if not options.silent:
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

    parser.add_option("--ignore-content", action="append", default=[])

    return parser



def main(args):
    parser = create_optparser()
    return cli(*parser.parse_args(args))



if __name__ == "__main__":
    sys.exit(main(sys.argv))



#
# The end.
