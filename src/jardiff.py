# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, see
# <http://www.gnu.org/licenses/>.



"""
Utility script and module for producing a set of changes in a JAR
file. Takes the same options as the classdiff script, and in fact uses
the classdiff script's code on each non-identical member in a pair of
JAR files.

author: Christopher O'Brien  <obriencj@gmail.com>
licence: LGPL
"""



from change import Change, GenericChange
from change import SuperChange, Addition, Removal
from change import yield_sorted_by_type



class JarTypeChange(GenericChange):
    # exploded vs. zipped and compression level

    label = "Jar type"

    def fn_data(self, c):
        # TODO: create some kind of menial zipinfo output showing type
        # (exploded/zipped) and compression level

        from os.path import isdir

        if(isdir(c)):
            return "exploded JAR"
        else:
            return "zipped JAR file"



class JarContentChange(Change):
    # a file or directory changed between JARs

    label = "Jar Content Changed"
    

    def __init__(self, lzip, rzip, entry, is_change=True):
        Change.__init__(self, lzip, rzip)
        self.entry = entry
        self.changed = is_change


    def get_description(self):
        if self.is_change():
            return "Jar Content Changed: " + self.entry
        else:
            return "Jar Content Unchanged: " + self.entry


    def is_ignored(self, options):
        from dirutils import fnmatches
        return fnmatches(self.entry, *options.ignore_jar_entry)



class JarContentAdded(JarContentChange, Addition):
    # A file or directory was added to a JAR

    label = "Jar Content Added"


    def is_ignored(self, options):
        from dirutils import fnmatches
        return fnmatches(self.entry, *options.ignore_jar_entry)

        # todo: check against ignored empty directories
        return False



class JarContentRemoved(JarContentChange, Removal):
    # A file or directory was removed from a JAR

    label = "Jar Content Removed"


    def is_ignored(self, options):
        from dirutils import fnmatches
        return fnmatches(self.entry, *options.ignore_jar_entry)

        # todo: check against ignored empty directories
        return False



class JarClassAdded(JarContentAdded):
    label = "Java Class Added"



class JarClassRemoved(JarContentRemoved):
    label = "Java Class Removed"



class JarClassChange(SuperChange, JarContentChange):
    label = "Java Class Changed"

    
    def __init__(self, ldata, rdata, entry, is_change=True):
        JarContentChange.__init__(self, ldata, rdata, entry, is_change)


    def collect_impl(self):
        from javaclass import unpack_class
        from classdiff import JavaClassChange

        if not self.is_change():
            return

        lfd = self.ldata.open(self.entry)
        rfd = self.rdata.open(self.entry)
        
        linfo = unpack_class(lfd)
        rinfo = unpack_class(rfd)

        lfd.close()
        rfd.close()

        yield JavaClassChange(linfo, rinfo)



class JarManifestChange(SuperChange, JarContentChange):
    label = "Jar Manifest Changed"

    
    def __init__(self, ldata, rdata, entry, is_change=True):
        JarContentChange.__init__(self, ldata, rdata, entry, is_change)


    def collect_impl(self):
        from manifest import Manifest, ManifestChange
        
        if not self.is_change():
            return

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



class JarSignatureAdded(JarContentAdded):
    label = "Jar Signature Added"



class JarSignatureRemoved(JarContentRemoved):
    label = "Jar Signature Removed"



class JarContentsChange(SuperChange):

    label = "JAR Contents"


    def __init__(self, left_fn, right_fn):
        SuperChange.__init__(self, left_fn, right_fn)
        self.lzip = None
        self.rzip = None


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
        from ziputils import compare_zips, LEFT, RIGHT, DIFF, SAME
        from dirutils import fnmatches

        # these are opened for the duration of check_impl
        left, right = self.lzip, self.rzip
        assert(left != None)
        assert(right != None)

        for event,entry in compare_zips(left, right):
            #print event, entry

            if event == SAME:

                # TODO: should we split by file type to more specific
                # types of (un)changes? For now just emit a content
                # change with is_change set to False.
                
                if entry == "META-INF/MANIFEST.MF":
                    yield JarManifestChange(left, right, entry, False)

                elif fnmatches(entry, "*.RSA", "*.DSA", "*.SF"):
                    yield JarSignatureChange(left, right, entry, False)

                elif fnmatches(entry, "*.class"):
                    yield JarClassChange(left, right, entry, False)
                    
                else:
                    yield JarContentChange(left, right, entry, False)

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


    def check_impl(self):

        """ overridden to open the left and right zipfiles and to
         provide all subchecks with an open ZipFile instance rather
         than having them all open and close the ZipFile individually.
         For the duration of the check (which calls collect_impl), the
         attributes self.lzip and self.rzip will be available and used
         as the ldata and rdata of all subchecks. """

        # this makes it work on exploded archives
        from ziputils import ZipFile

        lzip = ZipFile(self.ldata)
        rzip = ZipFile(self.rdata)

        self.lzip = lzip
        self.rzip = rzip

        ret = SuperChange.check_impl(self)

        lzip.close()
        rzip.close()

        self.lzip = None
        self.rzip = None

        return ret




class JarChange(SuperChange):
    label = "JAR"

    change_types = (JarTypeChange,
                    JarContentsChange)



# ---- Begin jardiff CLI ----
#



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
    left, right = rest[1:3]
    return cli_jars_diff(options, left, right)



def create_optparser():
    import classdiff
    parser = classdiff.create_optparser()

    parser.add_option("--ignore-jar-entry", action="append", default=[])

    return parser



def main(args):
    parser = create_optparser()
    return cli(*parser.parse_args(args))



#
# The end.
