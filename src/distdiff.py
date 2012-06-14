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
from change import yield_sorted_by_type



# glob patterns used to trigger a DistTextChange
TEXT_PATTERNS = (
    "*.bat",
    "*.cert",
    "*.cfg",
    "*.conf",
    "*.dtd",
    "*.html",
    "*.ini",
    "*.properties",
    "*.sh",
    "*.text",
    "*.txt",
    "*.xml",
)



class DistContentChange(Change):
    label = "Distributed Content"


    def __init__(self, ldir, rdir, entry, change=True):
        Change.__init__(self, ldir, rdir)
        self.entry = entry
        self.changed = change
        self.lineending = False
    

    def left_fn(self):
        from os.path import join
        return join(self.ldata, self.entry)


    def right_fn(self):
        from os.path import join
        return join(self.rdata, self.entry)


    def open_left(self, mode="rt"):
        return open(self.left_fn(), mode)


    def open_right(self, mode="rt"):
        return open(self.right_fn(), mode)
    

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



class DistTextChange(DistContentChange):
    label = "Distributed Text"


    def __init__(self, l, r, entry, change=True):
        DistContentChange.__init__(self, l, r, entry, change)
        self.lineending = False


    def check(self):
        from dirutils import fnmatches
        from itertools import izip_longest

        # We already know whether the file has changed or not, from
        # when it was created by the DistChange
        if not self.is_change():
            return

        # if the file matches what we would consider a text file,
        # check if the only difference is in the trailing whitespace,
        # and if so, set lineending to true so we can optionally
        # ignore the change later.
        with open(self.left_fn()) as lf, open(self.right_fn()) as rf:
            for li,ri in izip_longest(lf, rf, fillvalue=""):
                if li.rstrip() != ri.rstrip():
                    break
            else:
                # we went through every line, and they were all equal
                # when stripped of their trailing whitespace
                self.lineending = True

        return DistContentChange.check(self)


    def is_ignored(self, options):
        return (DistContentChange.is_ignored(self, options) or
                (self.lineending and options.ignore_trailing_whitespace))



class DistManifestChange(SuperChange, DistContentChange):
    label = "Distributed Manifest"
    

    def __init__(self, ldata, rdata, entry, change=True):
        SuperChange.__init__(self, ldata, rdata)
        DistContentChange.__init__(self, ldata, rdata, entry, change)


    def collect_impl(self):
        from manifest import Manifest, ManifestChange

        if not self.is_change():
            return
        
        lm, rm = Manifest(), Manifest()
        lm.parse_file(self.left_fn())
        rm.parse_file(self.right_fn())

        yield ManifestChange(lm, rm)        



class DistJarChange(SuperChange, DistContentChange):
    label = "Distributed JAR"


    def __init__(self, ldata, rdata, entry, change=True):
        SuperChange.__init__(self, ldata, rdata)
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



class DistJarReport(DistJarChange):

    def __init__(self, ldata, rdata, entry, reporter):
        DistJarChange.__init__(self, ldata, rdata, entry, True)
        self.reporter = reporter


    def collect_impl(self):
        from jardiff import JarReport
        from os.path import join

        lf = join(self.ldata, self.entry)
        rf = join(self.rdata, self.entry)

        if self.is_change():
            yield JarReport(lf, rf, self.reporter)



class DistJarAdded(DistContentAdded):
    label = "Distributed JAR Added"



class DistJarRemoved(DistContentRemoved):
    label = "Distributed JAR Removed"



class DistClassChange(SuperChange, DistContentChange):
    label = "Distributed Java Class"


    def __init__(self, ldata, rdata, entry, change=True):
        SuperChange.__init__(self, ldata, rdata)
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



class DistClassReport(DistClassChange):

    def __init__(self, l, r, entry, reporter):
        DistClassChange.__init__(self, l, r, entry, True)
        self.reporter = reporter


    def collect_impl(self):
        from javaclass import unpack_classfile
        from classdiff import JavaClassReport
        from os.path import join

        lf = join(self.ldata, self.entry)
        rf = join(self.rdata, self.entry)

        linfo = unpack_classfile(lf)
        rinfo = unpack_classfile(rf)

        if self.is_change():
            yield JavaClassReport(linfo, rinfo, self.reporter)



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

            elif deep and fnmatches(entry, *TEXT_PATTERNS):
                if event == LEFT:
                    yield DistContentRemoved(ld, rd, entry)
                elif event == RIGHT:
                    yield DistContentAdded(ld, rd, entry)
                elif event == DIFF:
                    yield DistTextChange(ld, rd, entry)
                elif event == SAME:
                    yield DistTextChange(ld, rd, entry, False)

            elif deep and fnmatches(entry, "*/MANIFEST.MF"):
                if event == LEFT:
                    yield DistContentRemoved(ld, rd, entry)
                elif event == RIGHT:
                    yield DistContentAdded(ld, rd, entry)
                elif event == DIFF:
                    yield DistManifestChange(ld, rd, entry)
                elif event == SAME:
                    yield DistManifestChange(ld, rd, entry, False)

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


    def __init__(self, l, r, reporter, shallow=False):
        DistChange.__init__(self, l, r, shallow)
        self.reporter = reporter


    def collect_impl(self):
        for c in DistChange.collect_impl(self):
            if isinstance(c, DistJarChange):
                if c.is_change():
                    nr = self.reporter.subreporter(c.entry, "jardiff")
                    c = DistJarReport(c.ldata, c.rdata, c.entry, nr)
            elif isinstance(c, DistClassChange):
                if c.is_change():
                    nr = self.reporter.subreporter(c.entry, "classdiff")
                    c = DistClassReport(c.ldata, c.rdata, c.entry, nr)
            yield c



    def check_impl(self):
        # overridden to immediately squash jar and class reports, to
        # save on memory usage.

        from change import squash

        changes = list()
        options = self.reporter.options

        c = False
        for change in self.collect_impl():
            change.check()
            c = c or change.is_change()

            if isinstance(change, (DistJarReport, DistClassReport)):
                changes.append(squash(change, options=options))
                change.clear()
            else:
                changes.append(change)

        self.changes = changes
        return c, None



    def check(self):
        # do the actual checking
        DistChange.check(self)

        # write to file
        self.reporter.run(self)



# ---- Begin distdiff CLI ----
#



def cli_dist_diff(parser, options, left, right):
    from report import Reporter
    from report import JSONReportFormat, TextReportFormat
    from report import CheetahReportFormat
    from sys import stdout

    reports = set(getattr(options, "reports", tuple()))
    if reports:
        rdir = options.report_dir or "./"
        rpt = Reporter(rdir, "distdiff", options)

        for fmt in reports:
            if fmt == "json":
                rpt.add_report_format(JSONReportFormat())
            elif fmt in ("txt", "text"):
                rpt.add_report_format(TextReportFormat())
            elif fmt in ("htm", "html"):
                rpt.add_report_format(CheetahReportFormat())
            else:
                parser.error("unknown report format: %s" % fmt)

        delta = DistReport(left, right, rpt, options.shallow)

    else:
        delta = DistChange(left, right, options.shallow)

    delta.check()

    if not options.silent:
        out = stdout
        if options.output:
            out = open(options.output, "wt")

        rpt = Reporter(None, None, options)
        if options.json:
            rpt.add_report_format(JSONReportFormat())
        else:
            rpt.add_report_format(TextReportFormat())
        rpt.run(delta, out)

        if options.output:
            out.close()
    
    if (not delta.is_change()) or delta.is_ignored(options):
        return 0
    else:
        return 1
    


def cli(parser, options, rest):
    if len(rest) != 3:
        parser.error("wrong number of arguments.")
    
    left, right = rest[1:3]
    return cli_dist_diff(parser, options, left, right)



def distdiff_optgroup(parser):
    from optparse import OptionGroup

    og = OptionGroup(parser, "Distribution Checking Options")

    og.add_option("--ignore-filenames", action="append", default=[])
    og.add_option("--ignore-trailing-whitespace",
                  action="store_true", default=False,
                  help="ignore trailing whitespace when comparing text files")

    return og



def create_optparser():
    from optparse import OptionParser
    from jardiff import jardiff_optgroup
    from classdiff import classdiff_optgroup, general_optgroup
    import report
    
    parser = OptionParser(usage="%prod [OPTIONS] OLD_DIST NEW_DIST")

    parser.add_option("--shallow", action="store_true", default=False)

    parser.add_option_group(general_optgroup(parser))
    parser.add_option_group(distdiff_optgroup(parser))
    parser.add_option_group(jardiff_optgroup(parser))
    parser.add_option_group(classdiff_optgroup(parser))

    parser.add_option_group(report.general_report_optgroup(parser))
    parser.add_option_group(report.json_report_optgroup(parser))
    parser.add_option_group(report.html_report_optgroup(parser))

    return parser



def main(args):
    parser = create_optparser()
    return cli(parser, *parser.parse_args(args))



#
# The end.
