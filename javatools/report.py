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


from __future__ import print_function


import sys

from abc import ABCMeta, abstractmethod
from argparse import Action
from Cheetah.DummyTransaction import DummyTransaction
from functools import partial
from json import dump, JSONEncoder
from os.path import exists, join, relpath
from six import add_metaclass
from six.moves import range

from .dirutils import copydir, makedirsp


_BUFFERING = 2 ** 16


__all__ = (
    "Reporter", "ReportFormat",
    "quick_report", "add_general_report_optgroup",
    "JSONReportFormat", "add_json_report_optgroup",
    "TextReportFormat",
    "CheetahReportFormat", "add_html_report_optgroup", )


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
            elif fmt in ("htm", "html"):
                self.add_report_format(CheetahReportFormat)


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


@add_metaclass(ABCMeta)
class ReportFormat(object):
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
            with open(fn, "wt", _BUFFERING) as out:
                self.run_impl(change, entry, out)
            return fn

        else:
            self.run_impl(change, entry, sys.stdout)
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


class _opt_cb_report(Action):

    """
    callback for the --report option in general_report_optgroup
    """
    def __call__(self, parser, options, values, option_string=None):

        if not hasattr(options, "reports"):
            options.reports = list()

        if "," in values:
            options.reports.extend(v for v in values.split(",") if v)
        else:
            options.reports.append(values)


def add_general_report_optgroup(parser):
    """
    General Reporting Options
    """

    g = parser.add_argument_group("Reporting Options")

    g.add_argument("--report-dir", action="store", default=None)

    g.add_argument("--report", action=_opt_cb_report,
                   help="comma-separated list of report formats")


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


def add_json_report_optgroup(parser):
    """
    Option group for the JSON report format
    """

    g = parser.add_argument_group("JSON Report Options")

    g.add_argument("--json-indent", action="store", default=2, type=int)


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
        # pylint: disable=E0202
        # JSONEncoder.default confuses pylint

        # if there is a simplify method, call it to convert the object
        # into a simplified dict
        if hasattr(o, "simplify"):
            return o.simplify(self.options)

        # handle sequences sanely
        try:
            i = iter(o)
        except TypeError:
            return JSONEncoder.default(self, o)
        else:
            return tuple(i)


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

    """ write a message to a text stream, with indentation. Also ensures that
    the output encoding of the messages is safe for writing. """

    for x in range(0, indent):
        stream.write("  ")
    for x in msgs:
        # Any nicer way? In Py2 x can be 'str' or 'unicode'.
        stream.write(x.encode("ascii", "backslashreplace").decode("ascii"))
    stream.write("\n")


class CheetahReportFormat(ReportFormat):
    """
    HTML output for a Change
    """

    extension = ".html"


    def _relative(self, uri):
        """
        if uri is relative, re-relate it to our basedir
        """

        if uri.startswith("http:") or \
           uri.startswith("https:") or \
           uri.startswith("file:") or \
           uri.startswith("/"):
            return uri

        elif exists(uri):
            return relpath(uri, self.basedir)

        else:
            return uri


    def _relative_uris(self, uri_list):
        """
        if uris in list are relative, re-relate them to our basedir
        """

        return [u for u in (self._relative(uri) for uri in uri_list) if u]


    def setup(self):
        """
        copies default stylesheets and javascript files if necessary, and
        appends them to the options
        """

        from javatools import cheetah

        options = self.options
        datadir = getattr(options, "html_copy_data", None)

        if getattr(options, "html_data_copied", False) or not datadir:
            # either already run by a parent report, or not supposed
            # to run at all.
            return

        # this is where we've installed the default media
        datasrc = join(cheetah.__path__[0], "data")

        # record the .js and .css content we copy
        javascripts = list()
        stylesheets = list()

        # copy the contents of our data source to datadir
        for _orig, copied in copydir(datasrc, datadir):
            if copied.endswith(".js"):
                javascripts.append(copied)
            elif copied.endswith(".css"):
                stylesheets.append(copied)

        javascripts.extend(getattr(options, "html_javascripts", tuple()))
        stylesheets.extend(getattr(options, "html_stylesheets", tuple()))

        options.html_javascripts = javascripts
        options.html_stylesheets = stylesheets

        # keep from copying again
        options.html_data_copied = True


    def run_impl(self, change, entry, out):
        """
        sets up the report directory for an HTML report. Obtains the
        top-level Cheetah template that is appropriate for the change
        instance, and runs it.

        The cheetah templates are supplied the following values:
         * change - the Change instance to report on
         * entry - the string name of the entry for this report
         * options - the cli options object
         * breadcrumbs - list of backlinks
         * javascripts - list of .js links
         * stylesheets - list of .css links

        The cheetah templates are also given a render_change method
        which can be called on another Change instance to cause its
        template to be resolved and run in-line.
        """

        options = self.options

        # translate relative paths if necessary
        javascripts = self._relative_uris(options.html_javascripts)
        stylesheets = self._relative_uris(options.html_stylesheets)

        # map the class of the change to a template class
        template_class = resolve_cheetah_template(type(change))

        # instantiate and setup the template
        template = template_class()

        # create a transaction wrapping the output stream
        template.transaction = DummyTransaction()
        template.transaction.response(resp=out)

        # inject our values
        template.change = change
        template.entry = entry
        template.options = options
        template.breadcrumbs = self.breadcrumbs
        template.javascripts = javascripts
        template.stylesheets = stylesheets

        # this lets us call render_change from within the template on
        # a change instance to chain to another template (eg, for
        # sub-changes)
        template.render_change = lambda c: self.run_impl(c, entry, out)

        # execute the template, which will write its contents to the
        # transaction (and the underlying stream)
        template.respond()

        # clean up the template
        template.shutdown()


def _compose_cheetah_template_map(cache):
    """
    does the work of composing the cheetah template map into the given
    cache
    """

    from .cheetah import get_templates

    # pylint: disable=W0406
    # needed for introspection
    import javatools

    for template_type in get_templates():
        if "_" not in template_type.__name__:
            # we use the _ to denote package and class names. So any
            # template without a _ in the name isn't meant to be
            # matched to a change type.
            continue

        # get the package and change class names based off of the
        # template class name
        tn = template_type.__name__
        pn, cn = tn.split("_", 1)

        # get the package from javatools
        pk = getattr(javatools, pn, None)
        if pk is None:
            __import__("javatools." + pn)
            pk = getattr(javatools, pn, None)

        # get the class from the package
        cc = getattr(pk, cn, None)
        if cc is None:
            raise Exception("no change class for template %s" % tn)

        # associate a Change class with a Template class
        cache[cc] = template_type

    return cache


# pylint: disable=C0103
_template_cache = dict()


def cheetah_template_map(cache=None):
    """
    a map of change types to cheetah template types. Used in
    resolve_cheetah_template
    """

    if cache is None:
        cache = _template_cache

    return cache or _compose_cheetah_template_map(cache)


def resolve_cheetah_template(change_type):
    """
    return the appropriate cheetah template class for the given change
    type, using the method-resolution-order of the change type.
    """

    tm = cheetah_template_map()

    # follow the built-in MRO for a type to find the matching
    # cheetah template
    for t in change_type.mro():
        tmpl = tm.get(t)
        if tmpl:
            return tmpl

    # this should never happen, since we'll provide a
    # change_Change template, and all of the changes should be
    # inheriting from that type
    raise Exception("No template for class %s" % change_type.__name__)


def add_html_report_optgroup(parser):
    """
    Option group for the HTML report format
    """

    g = parser.add_argument_group("HTML Report Options")

    g.add_argument("--html-stylesheet", action="append",
                   dest="html_stylesheets", default=list())

    g.add_argument("--html-javascript", action="append",
                   dest="html_javascripts", default=list())

    g.add_argument("--html-copy-data", action="store", default=None,
                   help="Copy default resources to the given directory and"
                   " enable them in the template")


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
        report.run(change, None, sys.stdout)


#
# The end.
