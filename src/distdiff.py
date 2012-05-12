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
Utility for comparing two distributions.

Distributions are directories. Any JAR files (eg: jar, sar, ear, war)
will be deeply checked for their class members. And Class files will
be checked for deep differences.

author: Christopher O'Brien  <obriencj@gmail.com>
license: LGPL
"""


from change import Change, GenericChange, SuperChange, Addition, Removal
from change import squash
from change import yield_sorted_by_type



class DistContentChange(Change):
    label = "Distributed Content"


    def __init__(self, ldir, rdir, entry, change=True):
        Change.__init__(self, ldir, rdir)
        self.entry = entry
        self.changed = change
    

    def get_description(self):
        c = ("has changed","is unchanged")[not self.is_change()]
        return "%s %s: %s" % (self.label, c, self.entry)


    def is_ignored(self, options):
        from dirutils import fnmatches
        return fnmatches(self.entry, *options.ignore_filenames)



class DistContentAdded(DistContentChange, Addition):
    label = "Distributed Content Added"
    
    def get_description(self):
        return "%s: %s" % (self.label, self.entry)



class DistContentRemoved(DistContentChange, Removal):
    label = "Distributed Content Removed"
    
    def get_description(self):
        return "%s: %s" % (self.label, self.entry)



class DistJarChange(SuperChange, DistContentChange):
    label = "Distributed JAR"


    def __init__(self, ldata, rdata, entry, change=True):
        DistContentChange.__init__(self, ldata, rdata, entry, change)


    def collect_impl(self):
        from jardiff import JarChange
        from os.path import join

        lf = join(self.ldata, self.entry)
        rf = join(self.rdata, self.entry)

        if self.is_change():
            yield JarChange(lf, rf)
    

    def get_description(self):
        return DistContentChange.get_description(self)



class DistJarAdded(DistContentAdded):
    label = "Distributed JAR Added"



class DistJarRemoved(DistContentRemoved):
    label = "Distributed JAR Removed"



class DistClassChange(SuperChange, DistContentChange):
    label = "Distributed Java Class"


    def __init__(self, ldata, rdata, entry, change=True):
        DistContentChange.__init__(self, ldata, rdata, entry, change)


    def collect_impl(self):
        from javaclass import unpack_classfile
        from classdiff import JavaClassChange
        from os.path import join

        lf = join(self.ldata, self.entry)
        rf = join(self.rdata, self.entry)

        linfo = unpack_classfile(lf)
        rinfo = unpack_classfile(rf)

        if self.is_change():
            yield JavaClassChange(linfo, rinfo)
    

    def get_description(self):
        return DistContentChange.get_description(self)



class DistClassAdded(DistContentAdded):
    label = "Distributed Java Class Added"



class DistClassRemoved(DistContentRemoved):
    label = "Distributed Java Class Removed"



class DistChange(SuperChange):
    label = "Distribution"


    def __init__(self, l, r, shallow=False):
        SuperChange.__init__(self, l, r)
        self.shallow = shallow


    def get_description(self):
        return "%s %s from %s to %s" % \
            (self.label, ("unchanged","changed")[self.is_change()],
             self.ldata, self.rdata)


    @yield_sorted_by_type(DistClassAdded,
                          DistClassRemoved,
                          DistClassChange,
                          DistJarAdded,
                          DistJarRemoved,
                          DistJarChange,
                          DistContentAdded,
                          DistContentRemoved,
                          DistContentChange)
    def collect_impl(self):
        from dirutils import compare, LEFT, RIGHT, SAME, DIFF
        from dirutils import fnmatches
        from jarinfo import JAR_PATTERNS

        ld, rd = self.ldata, self.rdata
        deep = not self.shallow

        for event,entry in compare(ld, rd):
            if deep and fnmatches(entry, *JAR_PATTERNS):
                if event == LEFT:
                    yield DistJarRemoved(ld, rd, entry)
                elif event == RIGHT:
                    yield DistJarAdded(ld, rd, entry)
                elif event == DIFF:
                    yield DistJarChange(ld, rd, entry)
                elif event == SAME:
                    yield DistJarChange(ld, rd, entry, False)

            elif deep and fnmatches(entry, "*.class"):
                if event == LEFT:
                    yield DistClassRemoved(ld, rd, entry)
                elif event == RIGHT:
                    yield DistClassAdded(ld, rd, entry)
                elif event == DIFF:
                    yield DistClassChange(ld, rd, entry)
                elif event == SAME:
                    yield DistClassChange(ld, rd, entry, False)

            else:
                if event == LEFT:
                    yield DistContentRemoved(ld, rd, entry)
                elif event == RIGHT:
                    yield DistContentAdded(ld, rd, entry)
                elif event == DIFF:
                    yield DistContentChange(ld, rd, entry)
                elif event == SAME:
                    yield DistContentChange(ld, rd, entry, False)



class DistReport(DistChange):

    """ This class has side-effects. Running the check method with the
    reportdir option set to True will cause the deep checks to be
    written to file in that directory """
    

    def __init__(self, l, r, options, shallow=False):
        DistChange.__init__(self, l, r, shallow)
        self.options = options


    def check_impl(self):
        squashed = list()
        
        overall_c = False

        options = self.options

        for change in self.collect_impl():

            change.check()
            c = change.is_change()
            i = change.is_ignored(options)

            squashed.append(squash(change, c, i))

            self.report(change)

            change.clear()
            del change

            overall_c = overall_c or c

        self.change = overall_c
        self.changes = tuple(squashed)

        return overall_c, None


    def report(self, change):
        from os.path import exists, split, join
        from os import makedirs

        opts = self.options
        reportdir = getattr(opts, "report_dir", None)

        extension = ("json", "txt")[not opts.json]

        if reportdir:
            d,f = split(change.entry)
            od = join(reportdir, d)

            if not exists(od):
                makedirs(od)
            
            f = "%s.report.%s" % (f, extension)

            # hackish, worth reconsidering use of options in write
            oldout = opts.output
            opts.output = join(od, f)
            change.write(opts)
            opts.output = oldout



def options_magic(options):
    from jardiff import options_magic
    return options_magic(options)



def cli(options, rest):
    from sys import stderr

    options_magic(options)
    
    left, right = rest[1:3]

    if options.report_dir:
        delta = DistReport(left, right, options, options.shallow)
    else:
        delta = DistChange(left, right, options.shallow)

    delta.check()

    if not options.silent:
        delta.write(options)
    
    if (not delta.is_change()) or delta.is_ignored(options):
        return 0
    else:
        return 1



def create_optiongroup(parser):
    from optparse import OptionGroup

    og = OptionGroup(parser, "Distribution Checking Options")

    og.add_option("--ignore-filenames", action="append", default=[])

    return og



def create_optparser():
    from optparse import OptionParser
    from jardiff import jardiff_optiongroup
    from classdiff import classdiff_optiongroup
    
    parser = OptionParser(usage="%prod [options] old_dist new_dist")

    parser.add_option("--shallow", action="store_true", default=False)
    parser.add_option("--report-dir", action="store", default=None)

    parser.add_group(create_optiongroup(parser))
    parser.add_group(jardiff_optiongroup(parser))
    parser.add_group(classdiff_optiongroup(parser)

    return parser



def main(args):
    parser = create_optparser()
    return cli(*parser.parse_args(args))



#
# The end.
