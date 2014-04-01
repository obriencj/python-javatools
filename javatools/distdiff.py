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



from itertools import izip_longest
from os.path import join

from javatools import unpack_classfile
from .change import SuperChange, Addition, Removal
from .change import squash, yield_sorted_by_type
from .classdiff import JavaClassChange, JavaClassReport
from .dirutils import compare, fnmatches
from .dirutils import LEFT, RIGHT, SAME, DIFF
from .manifest import Manifest, ManifestChange
from .jardiff import JarChange, JarReport
from .jarinfo import JAR_PATTERNS



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



class DistContentChange(SuperChange):

    label = "Distributed Content"


    def __init__(self, ldir, rdir, entry, change=True):
        SuperChange.__init__(self, ldir, rdir)
        self.entry = entry
        self.changed = change


    def left_fn(self):
        return join(self.ldata, self.entry)


    def right_fn(self):
        return join(self.rdata, self.entry)


    def open_left(self, mode="rb"):
        return open(self.left_fn(), mode)


    def open_right(self, mode="rb"):
        return open(self.right_fn(), mode)


    def collect_impl(self):

        """ Content changes refer to more concrete children, but by
        default are empty """

        return tuple()


    def get_description(self):
        c = ("has changed","is unchanged")[not self.is_change()]
        return "%s %s: %s" % (self.label, c, self.entry)


    def is_ignored(self, options):
        return (fnmatches(self.entry, *options.ignore_filenames) or
                SuperChange.is_ignored(self, options))



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
        # We already know whether the file has changed or not, from
        # when it was created by the DistChange
        if not self.is_change():
            return

        # if the file matches what we would consider a text file,
        # check if the only difference is in the trailing whitespace,
        # and if so, set lineending to true so we can optionally
        # ignore the change later.
        with self.open_left(mode="rt") as lfd:
            with self.open_right(mode="rt") as rfd:
                for li, ri in izip_longest(lfd, rfd, fillvalue=""):
                    if li.rstrip() != ri.rstrip():
                        self.lineending = False
                        break
                else:
                    # we went through every line, and they were all equal
                    # when stripped of their trailing whitespace
                    self.lineending = True

        return DistContentChange.check(self)


    def is_ignored(self, options):
        return (DistContentChange.is_ignored(self, options) or
                (self.lineending and options.ignore_trailing_whitespace))



class DistManifestChange(DistContentChange):

    """ A MANIFEST.MF file found in the directory structure of the
    distribution """


    label = "Distributed Manifest"


    def collect_impl(self):
        if self.is_change():
            with self.open_left(mode="rt") as fd:
                left_m = Manifest()
                left_m.parse(fd)

            with self.open_right(mode="rt") as fd:
                right_m = Manifest()
                right_m.parse(fd)

            yield ManifestChange(left_m, right_m)



class DistJarChange(DistContentChange):

    label = "Distributed JAR"


    def collect_impl(self):
        if self.is_change():
            yield JarChange(self.left_fn(), self.right_fn())


    def get_description(self):
        return DistContentChange.get_description(self)



class DistJarReport(DistJarChange):

    report_name = "JarReport"


    def __init__(self, ldata, rdata, entry, reporter):
        DistJarChange.__init__(self, ldata, rdata, entry, True)
        self.reporter = reporter


    def collect_impl(self):
        if self.is_change():
            yield JarReport(self.left_fn(), self.right_fn(), self.reporter)



class DistJarAdded(DistContentAdded):

    label = "Distributed JAR Added"



class DistJarRemoved(DistContentRemoved):

    label = "Distributed JAR Removed"



class DistClassChange(DistContentChange):

    label = "Distributed Java Class"


    def collect_impl(self):
        if self.is_change():
            linfo = unpack_classfile(self.left_fn())
            rinfo = unpack_classfile(self.right_fn())

            yield JavaClassChange(linfo, rinfo)


    def get_description(self):
        return DistContentChange.get_description(self)



class DistClassReport(DistClassChange):

    report_name = "JavaClassReport"


    def __init__(self, l, r, entry, reporter):
        DistClassChange.__init__(self, l, r, entry, True)
        self.reporter = reporter


    def collect_impl(self):
        if self.is_change():
            linfo = unpack_classfile(self.left_fn())
            rinfo = unpack_classfile(self.right_fn())

            yield JavaClassReport(linfo, rinfo, self.reporter)



class DistClassAdded(DistContentAdded):

    label = "Distributed Java Class Added"



class DistClassRemoved(DistContentRemoved):

    label = "Distributed Java Class Removed"



class DistChange(SuperChange):

    """ Top-level change for comparing two distributions """

    label = "Distribution"


    def __init__(self, left, right, shallow=False):
        SuperChange.__init__(self, left, right)
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
                          DistTextChange,
                          DistManifestChange,
                          DistContentAdded,
                          DistContentRemoved,
                          DistContentChange)
    def collect_impl(self):

        """ emits change instances based on the delta of the two
        distribution directories """

        ld = self.ldata
        rd = self.rdata
        deep = not self.shallow

        for event, entry in compare(ld, rd):
            if deep and fnmatches(entry, *JAR_PATTERNS):
                if event == LEFT:
                    yield DistJarRemoved(ld, rd, entry)
                elif event == RIGHT:
                    yield DistJarAdded(ld, rd, entry)
                elif event == DIFF:
                    yield DistJarChange(ld, rd, entry, True)
                elif event == SAME:
                    yield DistJarChange(ld, rd, entry, False)

            elif deep and fnmatches(entry, "*.class"):
                if event == LEFT:
                    yield DistClassRemoved(ld, rd, entry)
                elif event == RIGHT:
                    yield DistClassAdded(ld, rd, entry)
                elif event == DIFF:
                    yield DistClassChange(ld, rd, entry, True)
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
                    yield DistManifestChange(ld, rd, entry, True)
                elif event == SAME:
                    yield DistManifestChange(ld, rd, entry, False)

            else:
                if event == LEFT:
                    yield DistContentRemoved(ld, rd, entry)
                elif event == RIGHT:
                    yield DistContentAdded(ld, rd, entry)
                elif event == DIFF:
                    yield DistContentChange(ld, rd, entry, True)
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
        create up to process_count helper processes and use them to
        perform the DistJarReport and DistClassReport actions. """

        from multiprocessing import Process, Queue

        options = self.reporter.options

        # this is the function that will be run in a separate process,
        # which will handle the tasks queue and feed into the results
        # queue
        func = _mp_run_check

        # normally this would happen lazily, but since we'll have
        # multiple processes all running reports at the same time, we
        # need to make sure the setup is done before-hand. This is
        # hackish, but in particular this keeps the HTML reports from
        # trying to perform the default data copy over and over.
        self.reporter.setup()

        # enqueue the sub-reports for multi-processing. Other types of
        # changes can happen sync.
        changes = list(self.collect_impl())

        task_count = 0
        tasks = Queue()
        results = Queue()

        try:
            # as soon as we start using the tasks queue, we need to be
            # catching the KeyboardInterrupt event so that we can
            # drain the queue and lets its underlying thread terminate
            # happily.

            # TODO: is there a better way to handle this shutdown
            # gracefully?

            # feed any sub-reports to the tasks queue
            for index in xrange(0, len(changes)):
                change = changes[index]
                if isinstance(change, (DistJarReport, DistClassReport)):
                    changes[index] = None
                    tasks.put((index, change))
                    task_count += 1

            # infrequent edge case, but don't bother starting more
            # helpers than we'll ever use
            process_count = min(process_count, task_count)

            # start the number of helper processes, and make sure
            # there are that many stop sentinels at the end of the
            # tasks queue
            for _i in xrange(0, process_count):
                tasks.put(None)
                process = Process(target=func, args=(tasks, results, options))
                process.daemon = False
                process.start()

            # while the helpers are running, perform our checks
            for change in changes:
                if change:
                    change.check()

            # get all of the results and feed them back into our change
            for _i in xrange(0, task_count):
                index, change = results.get()
                changes[index] = change

        except KeyboardInterrupt, keyint:
            # drain the tasks queue so it will exit gracefully
            for change in iter(tasks.get, None):
                pass
            raise keyint

        # complete the check by setting our internal collection of
        # child changes and returning our overall status
        c = False
        for change in changes:
            c = c or change.is_change()
        self.changes = changes
        return c, None


    def check_impl(self):
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



def _mp_run_check(tasks, results, options):

    """ a helper function for multiprocessing with DistReport. """

    try:
        for index, change in iter(tasks.get, None):
            # this is the part that takes up all of our time and
            # produces side-effects like writing out files for all of
            # the report formats.
            change.check()

            # rather than serializing the completed change (which
            # could be rather large now that it's been realized), we
            # send back only what we want, which is the squashed
            # overview, and throw away the used bits.
            squashed = squash(change, options=options)
            change.clear()

            results.put((index, squashed))

    except KeyboardInterrupt:
        # prevent a billion lines of backtrace from hitting the user
        # in the face
        return



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
    from multiprocessing import cpu_count

    # for the --processes default
    cpus = cpu_count()

    og = OptionGroup(parser, "Distribution Checking Options")

    og.add_option("--processes", action="store",
                  type="int", default=cpus,
                  help="Number of child processes to spawn to handle"
                  " sub-reports. Set to 0 to disable multi-processing."
                  " Defaults to the number of CPUs (%r)" % cpus)

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

    parser = OptionParser(usage="%prog [OPTIONS] OLD_DIST NEW_DIST")

    parser.add_option_group(general_optgroup(parser))
    parser.add_option_group(distdiff_optgroup(parser))
    parser.add_option_group(jardiff_optgroup(parser))
    parser.add_option_group(classdiff_optgroup(parser))

    parser.add_option_group(report.general_report_optgroup(parser))
    parser.add_option_group(report.json_report_optgroup(parser))
    parser.add_option_group(report.html_report_optgroup(parser))

    return parser



def default_distdiff_options(updates=None):

    """ generate an options object with the appropriate default values
    in place for API usage of distdiff features. overrides is an
    optional dictionary which will be used to update fields on the
    options object. """

    parser = create_optparser()
    options, _args = parser.parse_args(list())

    if updates:
        #pylint: disable=W0212
        options._update_careful(updates)

    return options



def main(args):

    """ entry point for the distdiff command-line utility """

    parser = create_optparser()
    return cli(parser, *parser.parse_args(args))



#
# The end.
