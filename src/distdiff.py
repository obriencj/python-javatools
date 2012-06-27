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


from .change import Change, SuperChange
from .change import Addition, Removal
from .change import yield_sorted_by_type



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
        from .dirutils import fnmatches
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
        from itertools import izip_longest

        # We already know whether the file has changed or not, from
        # when it was created by the DistChange
        if not self.is_change():
            return

        # if the file matches what we would consider a text file,
        # check if the only difference is in the trailing whitespace,
        # and if so, set lineending to true so we can optionally
        # ignore the change later.

        with open(self.left_fn()) as lf:
            with open(self.right_fn()) as rf:
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
        from .manifest import Manifest, ManifestChange

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
        from .jardiff import JarChange
        from os.path import join

        lf = join(self.ldata, self.entry)
        rf = join(self.rdata, self.entry)

        if self.is_change():
            yield JarChange(lf, rf)
    

    def get_description(self):
        return DistContentChange.get_description(self)



class DistJarReport(DistJarChange):

    report_name = "JarReport"


    def __init__(self, ldata, rdata, entry, reporter):
        DistJarChange.__init__(self, ldata, rdata, entry, True)
        self.reporter = reporter


    def collect_impl(self):
        from .jardiff import JarReport
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
        from javatools import unpack_classfile
        from .classdiff import JavaClassChange
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

    report_name = "JavaClassReport"


    def __init__(self, l, r, entry, reporter):
        DistClassChange.__init__(self, l, r, entry, True)
        self.reporter = reporter


    def collect_impl(self):
        from javatools import unpack_classfile
        from .classdiff import JavaClassReport
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

    """ Top-level change for comparing two distributions """

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

        """ emits change instances based on the delta of the two
        distribution directories """

        from .dirutils import LEFT, RIGHT, SAME, DIFF
        from .dirutils import compare, fnmatches
        from .jarinfo import JAR_PATTERNS

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

    report_name = "DistReport"


    def __init__(self, l, r, reporter):
        self.reporter = reporter
        options = reporter.options
        shallow = getattr(options, "shallow", False)
        DistChange.__init__(self, l, r, shallow)


    def collect_impl(self):

        """ overrides DistJarChange and DistClassChange from the
        underlying DistChange with DistJarReport and DistClassReport
        instances """

        for c in DistChange.collect_impl(self):
            if isinstance(c, DistJarChange):
                if c.is_change():
                    ln = DistJarReport.report_name
                    nr = self.reporter.subreporter(c.entry, ln)
                    c = DistJarReport(c.ldata, c.rdata, c.entry, nr)
            elif isinstance(c, DistClassChange):
                if c.is_change():
                    ln = DistClassReport.report_name
                    nr = self.reporter.subreporter(c.entry, ln)
                    c = DistClassReport(c.ldata, c.rdata, c.entry, nr)
            yield c


    def mp_check_impl(self, process_count):

        """ a multiprocessing-enabled check implementation. Will
        create process_count helper processes and use them to perform
        the DistJarReport and DistClassReport actions. """

        from multiprocessing import Process, Queue

        options = self.reporter.options

        task_count = 0
        tasks = Queue()
        results = Queue()

        # this is the function that will be run in a separate process,
        # which will handle the tasks queue and feed into the results
        # queue
        func = _mp_check_helper

        # enqueue the sub-reports for multi-processing. Other types of
        # changes can happen sync.
        changes = list(self.collect_impl())
        for index in xrange(0, len(changes)):
            change = changes[index]

            if isinstance(change, (DistJarReport, DistClassReport)):
                changes[index] = None
                tasks.put((index, change))
                task_count += 1
            else:
                change.check()

        # start the number of processes, and make sure there are that
        # many stop sentinels in the tasks queue
        for _i in xrange(0, process_count):
            tasks.put(None)
            process = Process(target=func, args=(tasks, results, options))
            process.start()
        
        # get all of the results and feed them back into our change
        for _i in xrange(0, task_count):
            index, change = results.get()
            changes[index] = change

        # complete the check by setting our internal collection of
        # child changes and returning our overall status
        c = False
        for change in changes:
            c = c or change.is_change()
        self.changes = changes
        return c, None


    def check_impl(self):
        from .change import squash

        options = self.reporter.options

        # if we're configured to use multiple processes, the work happens
        # in mp_check_impl instead
        forks = getattr(options, "processes", 0)
        if forks:
            return self.mp_check_impl(forks)

        changes = list()

        c = False
        for change in self.collect_impl():
            change.check()
            c = c or change.is_change()

            if isinstance(change, (DistJarReport, DistClassReport)):
                # the child report has run, we only need to keep the
                # squashed overview
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



def _mp_check_helper(tasks, results, options):

    """ a helper function for multiprocessing with DistReport. """

    from .change import squash

    for index, change in iter(tasks.get, None):

        # this is the part that takes up all of our time and produces
        # side-effects like writing out files for all of the report
        # formats.
        change.check()

        # rather than serializing the completed change (which could be
        # rather large now that it's been realized), we send back only
        # what we want, which is the squashed overview, and throw away
        # the used bits.
        squashed = squash(change, options=options)
        change.clear()

        results.put((index, squashed))



# ---- Begin distdiff CLI ----
#



def cli_dist_diff(parser, options, left, right):
    from .report import quick_report, Reporter
    from .report import JSONReportFormat, TextReportFormat

    reports = getattr(options, "reports", tuple())
    if reports:
        rdir = options.report_dir or "./"

        rpt = Reporter(rdir, "DistReport", options)
        rpt.add_formats_by_name(reports)

        delta = DistReport(left, right, rpt)

    else:
        delta = DistChange(left, right, options.shallow)

    delta.check()

    if not options.silent:
        if options.json:
            quick_report(JSONReportFormat, delta, options)
        else:
            quick_report(TextReportFormat, delta, options)
    
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

    """ Option group relating to the use of a DistChange or DistReport """

    from optparse import OptionGroup

    og = OptionGroup(parser, "Distribution Checking Options")

    og.add_option("--processes", action="store", type="int", default=0,
                  help="Number of child processes to spawn to handle"
                  " sub-reports. Defaults to 0")

    og.add_option("--shallow", action="store_true", default=False,
                  help="Check only that the files of this dist have"
                  "changed, do not infer the meaning")

    og.add_option("--ignore-filenames", action="append", default=[],
                  help="file glob to ignore. Can be specified multiple"
                  " times")

    og.add_option("--ignore-trailing-whitespace",
                  action="store_true", default=False,
                  help="ignore trailing whitespace when comparing text"
                  " files")

    return og



def create_optparser():

    """ an OptionParser instance filled with options and groups
    appropriate for use with the distdiff command """

    from optparse import OptionParser
    from .jardiff import jardiff_optgroup
    from .classdiff import classdiff_optgroup, general_optgroup
    from javatools import report
    
    parser = OptionParser(usage="%prod [OPTIONS] OLD_DIST NEW_DIST")

    parser.add_option_group(general_optgroup(parser))
    parser.add_option_group(distdiff_optgroup(parser))
    parser.add_option_group(jardiff_optgroup(parser))
    parser.add_option_group(classdiff_optgroup(parser))

    parser.add_option_group(report.general_report_optgroup(parser))
    parser.add_option_group(report.json_report_optgroup(parser))
    parser.add_option_group(report.html_report_optgroup(parser))

    return parser



def main(args):

    """ entry point for the distdiff command-line utility """

    parser = create_optparser()
    return cli(parser, *parser.parse_args(args))



#
# The end.
