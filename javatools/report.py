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
Classes for representing changes as formatted text.

:author: Christopher O'Brien  <obriencj@gmail.com>
:license: LGPL
"""

from future.utils import with_metaclass

from abc import ABCMeta, abstractmethod
from functools import partial
from json import dump, JSONEncoder
from optparse import OptionGroup
from os.path import exists, join, relpath
from sys import stdout
from .dirutils import copydir, makedirsp


_BUFFERING = 2 ** 16


__all__ = (
    "Reporter", "ReportFormat",
    "quick_report", "general_report_optgroup",
    "JSONReportFormat", "json_report_optgroup",
    "TextReportFormat",
    # "CheetahReportFormat", "html_report_optgroup",
)


class Reporter(object):
    """
    Collects multiple report formats for use in presenting a change
    """


    def __init__(self, basedir, entry, options):
        self.basedir = basedir
        self.entry = entry
        self.options = options
        self.breadcrumbs = tuple()
        self.formats = set()

        # cache of instances from self.formats, created in setup, used
        # in run, removed in clear
        self._formats = None


    def get_relative_breadcrumbs(self):
        """
        get the breadcrumbs as relative to the basedir
        """

        basedir = self.basedir
        crumbs = self.breadcrumbs

        return [(relpath(b, basedir), e) for b, e in crumbs]


    def add_formats_by_name(self, rfmt_list):
        """
        adds formats by short label descriptors, such as 'txt', 'json', or
        'html'
        """

        for fmt in rfmt_list:
            if fmt == "json":
                self.add_report_format(JSONReportFormat)
            elif fmt in ("txt", "text"):
                self.add_report_format(TextReportFormat)
            # elif fmt in ("htm", "html"):
            #     self.add_report_format(CheetahReportFormat)


    def add_report_format(self, report_format):
        """
        Add an output format to this reporter. report_format should be a
        ReportFormat subtype. It will be instantiated when the
        reporter is run.
        """

        self.formats.add(report_format)


    def subreporter(self, subpath, entry):
        """
        create a reporter for a sub-report, with updated breadcrumbs and
        the same output formats
        """

        newbase = join(self.basedir, subpath)
        r = Reporter(newbase, entry, self.options)

        crumbs = list(self.breadcrumbs)
        crumbs.append((self.basedir, self.entry))
        r.breadcrumbs = crumbs

        r.formats = set(self.formats)
        return r


    def setup(self):
        """
        instantiates all report formats that have been added to this
        reporter, and calls their setup methods.
        """

        if self._formats:
            # setup has been run already.
            return

        basedir = self.basedir
        options = self.options
        crumbs = self.get_relative_breadcrumbs()

        fmts = list()
        for fmt_class in self.formats:
            fmt = fmt_class(basedir, options, crumbs)
            fmt.setup()
            fmts.append(fmt)

        self._formats = fmts


    def run(self, change):
        """
        runs the report format instances in this reporter. Will call setup
        if it hasn't been called already
        """

        if self._formats is None:
            self.setup()

        entry = self.entry

        for fmt in self._formats:
            fmt.run(change, entry)

        self.clear()


    def clear(self):
        """
        calls clear on any report format instances created during setup
        and drops the cache
        """

        if self._formats:
            for fmt in self._formats:
                fmt.clear()
        self._formats = None


class ReportFormat(with_metaclass(ABCMeta, object)):
    """
    Base class of a report format provider. Override to describe a
    concrete format type
    """


    extension = ".report"


    def __init__(self, basedir, options, breadcrumbs=tuple()):
        self.basedir = basedir
        self.options = options
        self.breadcrumbs = breadcrumbs


    @abstractmethod
    def run_impl(self, change, entry, out):
        """
        override to actually produce output
        """

        pass


    def run(self, change, entry, out=None):
        """
        setup for run, including creating an output file if needed. Calls
        run_impl when ready. If out and entry are both None,
        sys.stdout is used
        """

        if out:
            self.run_impl(change, entry, out)
            return None

        elif entry:
            basedir = self.basedir or "./"

            makedirsp(basedir)

            fn = join(basedir, entry + self.extension)
            with open(fn, "wb", _BUFFERING) as out:
                self.run_impl(change, entry, out)
            return fn

        else:
            self.run_impl(change, entry, stdout)
            return None


    def setup(self):
        """
        override if the report format has behavior which can be done ahead
        of time, such as copying files or creating directories
        """

        pass


    def clear(self):
        """
        clear up the internal references of this format. Called by the
        parent reporter at the end of run
        """

        self.basedir = None
        self.options = None
        self.breadcrumbs = None


def _opt_cb_report(_opt, _optstr, value, parser):
    """
    callback for the --report option in general_report_optgroup
    """

    options = parser.values

    if not hasattr(options, "reports"):
        options.reports = list()

    if "," in value:
        options.reports.extend(v for v in value.split(",") if v)
    else:
        options.reports.append(value)


def general_report_optgroup(parser):
    """
    General Reporting Options
    """

    g = OptionGroup(parser, "Reporting Options")

    g.add_option("--report-dir", action="store", default=None)

    g.add_option("--report", action="callback", type="string",
                 help="comma-separated list of report formats",
                 callback=_opt_cb_report)

    return g


class JSONReportFormat(ReportFormat):
    """
    renders a Change and all of its children to a JSON object. Can use
    options from the jon_report_optgroup option group
    """

    extension = ".json"


    def run_impl(self, change, entry, out):
        options = self.options
        indent = getattr(options, "json_indent", 2)

        data = {
            "runtime_options": options.__dict__,
            "report": change,
            }

        # not what they expected, but it works
        cls = partial(JSONChangeEncoder, options)

        try:
            dump(data, out, sort_keys=True, indent=indent, cls=cls)

        except TypeError:
            # XXX for debugging. Otherwise the wrapping try isn't necessary
            print(data)
            raise


def json_report_optgroup(parser):
    """
    Option group for the JON report format
    """

    g = OptionGroup(parser, "JON Report Options")

    g.add_option("--json-indent", action="store", default=2)

    return g


class JSONChangeEncoder(JSONEncoder):
    """
    A specialty JSONEncoder which knows how to represent Change
    instances (or anything with a simplify method), and sequences (by
    rendering them into tuples)
    """


    def __init__(self, options, *a, **k):
        JSONEncoder.__init__(self, *a, **k)
        self.options = options


    def default(self, o):
        #pylint: disable=E0202
        # JSONEncoder.default confuses pylint

        # if there is a simplify method, call it to convert the object
        # into a simplified dict
        if hasattr(o, "simplify"):
            return o.simplify(self.options)

        # handle sequences sanely
        try:
            i = iter(o)
        except TypeError:
            pass
        else:
            return tuple(i)

        return JSONEncoder.default(self, o)


class TextReportFormat(ReportFormat):
    """
    Renders the change as indented text
    """

    extension = ".text"


    def run_impl(self, change, entry, out):
        options = self.options
        _indent_change(change, out, options, 0)


def _indent_change(change, out, options, indent):
    """
    recursive function to print indented change descriptions
    """

    show_unchanged = getattr(options, "show_unchanged", False)
    show_ignored = getattr(options, "show_ignored", False)

    show = False
    desc = change.get_description()

    if change.is_change():
        if change.is_ignored(options):
            if show_ignored:
                show = True
                _indent(out, indent, desc, " [IGNORED]")
        else:
            show = True
            _indent(out, indent, desc)
    elif show_unchanged:
        show = True
        _indent(out, indent, desc)

    if show:
        indent += 1
        for sub in change.collect():
            _indent_change(sub, out, options, indent)


def _indent(stream, indent, *msgs):

    """ write a message to stream, with indentation. Also ensures that
    the output encoding of the messages is safe for writing. """

    for x in xrange(0, indent):
        stream.write("  ")
    for x in msgs:
        stream.write(x.encode("ascii", "backslashreplace"))
    stream.write("\n")


def quick_report(report_type, change, options):
    """
    writes a change report via report_type to options.output or
    sys.stdout
    """

    report = report_type(None, options)

    if options.output:
        with open(options.output, "w") as out:
            report.run(change, None, out)
    else:
        report.run(change, None, stdout)


#
# The end.
