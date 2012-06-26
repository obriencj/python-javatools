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

author: Christopher O'Brien  <obriencj@gmail.com>
license: LGPL
"""



from json import JSONEncoder



class Reporter(object):

    """ Collects multiple report formats for use in presenting a
    change """


    def __init__(self, basedir, entry, options):
        self.basedir = basedir
        self.entry = entry
        self.options = options
        self.breadcrumbs = tuple()
        self.formats = set()


    def get_relative_breadcrumbs(self):

        """ get the breadcrumbs as relative to the basedir """

        from os.path import relpath

        basedir = self.basedir
        crumbs = self.breadcrumbs

        return [(relpath(b, basedir), e) for b, e in crumbs]


    def add_formats_by_name(self, rfmt_list):

        """ adds formats by short label descriptors, such as 'txt',
        'json', or 'html' """

        for fmt in rfmt_list:
            if fmt == "json":
                self.add_report_format(JSONReportFormat)
            elif fmt in ("txt", "text"):
                self.add_report_format(TextReportFormat)
            elif fmt in ("htm", "html"):
                self.add_report_format(CheetahReportFormat)


    def add_report_format(self, report_format):
        
        """ Add an output format to this reporter. report_format
        should be a ReportFormat subtype. It will be instantiated when
        the reporter is run. """

        self.formats.add(report_format)


    def subreporter(self, subpath, entry):

        """ create a reporter for a sub-report, with updated
        breadcrumbs and the same output formats """

        from os.path import join

        newbase = join(self.basedir, subpath)
        r = Reporter(newbase, entry, self.options)

        crumbs = list(self.breadcrumbs)
        crumbs.append((self.basedir, self.entry))
        r.breadcrumbs = crumbs

        r.formats = set(self.formats)
        return r


    def run(self, change):

        """ Instantiates all report formats that have been added to
        this reporter, and runs them """

        basedir = self.basedir
        options = self.options
        crumbs = self.get_relative_breadcrumbs()
        entry = self.entry

        # formats is a set of types
        for fmt_class in self.formats:
            # instantiate a formater from the class and run it
            fmt = fmt_class(basedir, options, crumbs)
            fmt.run(change, entry)



class ReportFormat(object):

    """ Base class of a report format provider. Override to describe a
    concrete format type """
    

    extension = ".report"


    def __init__(self, basedir, options, breadcrumbs=tuple()):
        self.basedir = basedir
        self.options = options
        self.breadcrumbs = breadcrumbs


    def run_impl(self, change, entry, out):
        
        """ override to actually produce output """

        pass


    def run(self, change, entry, out=None):

        """ setup for run, including creating an output file if
        needed. Calls run_impl when ready """

        from os.path import exists, join
        from os import makedirs
        from sys import stdout

        if out:
            self.run_impl(change, entry, out)
            return None
        
        elif entry:
            basedir = self.basedir or "./"

            if not exists(basedir):
                makedirs(basedir)

            fn = join(basedir, entry + self.extension)
            with open(fn, "wt") as out:
                self.run_impl(change, entry, out)
            return fn

        else:
            self.run_impl(change, entry, stdout)
            return None



def _opt_cb_report(_opt, _optstr, value, parser):

    """ callback for the --report option in general_report_optgroup """

    options = parser.values
    
    if not hasattr(options, "reports"):
        options.reports = list()

    if "," in value:
        options.reports.extend(v for v in value.split(",") if v)
    else:
        options.reports.append(value)



def general_report_optgroup(parser):

    """ General Reporting Options """

    from optparse import OptionGroup

    g = OptionGroup(parser, "Reporting Options")

    g.add_option("--report-dir", action="store", default=None)

    g.add_option("--report", action="callback", type="string",
                 help="comma-separated list of report formats",
                 callback=_opt_cb_report)

    return g



class JSONReportFormat(ReportFormat):

    """ renders a Change and all of its children to a JSON object. Can
    use options from the jon_report_optgroup option group """
    
    extension = ".json"


    def run_impl(self, change, entry, out):
        from json import dump

        options = self.options
        indent = getattr(options, "json_indent", 2)

        data = {
            "runtime_options": options.__dict__,
            "report": change,
            }

        # not what they expected, but it works
        cls = lambda *a,**k: JSONChangeEncoder(options, *a, **k)

        #print data
        try:
            dump(data, out, sort_keys=True, indent=indent, cls=cls)
        except TypeError, te:
            print data
            raise(te)



def json_report_optgroup(parser):

    """ Option group for the JON report format """

    from optparse import OptionGroup

    g = OptionGroup(parser, "JON Report Options")

    g.add_option("--json-indent", action="store", default=2)

    return g



class JSONChangeEncoder(JSONEncoder):

    """ A specialty JSONEncoder which knows how to represent Change
    instances (or anything with a simplify method), and sequences (by
    rendering them into tuples) """


    def __init__(self, options, *a,**k):
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

    """ Renders the change as indented text """

    extension = ".text"


    def run_impl(self, change, entry, out):
        options = self.options
        _indent_change(change, out, options, 0)



def _indent_change(change, out, options, indent):

    """ recursive function to print indented change descriptions """

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

    for x in xrange(0,indent):
        stream.write("  ")
    for x in msgs:
        stream.write(x.encode("ascii", errors="backslashreplace"))
    stream.write("\n")



class CheetahReportFormat(ReportFormat):

    """ HTML output for a Change """
    
    extension = ".html"


    def _relative(self, uri):

        """ if uri is relative, re-relate it to our basedir """

        from os.path import exists, relpath
        
        if (uri.startswith("http:") or
            uri.startswith("https:") or
            uri.startswith("file:") or
            uri.startswith("/")):
            return uri

        elif exists(uri):
            result = relpath(uri, self.basedir)
            #print uri, self.basedir, result
            return result

        else:
            return uri


    def _relative_uris(self, uri_list):

        """ if uris in list are relative, re-relate them to our basedir """

        return [u for u in (self._relative(uri) for uri in uri_list) if u]


    def copy_data(self):

        """ copies default stylesheets and javascript files if
        necessary, and appends them to the options """

        from javatools import cheetah
        from shutil import copy
        from os.path import exists, join, relpath
        from os import makedirs, walk
        
        options = self.options
        datadir = getattr(options, "html_copy_data", None)
        copied = getattr(options, "html_data_copied", False)
        
        if copied or not datadir:
            return

        # this is where we've installed the default media
        datasrc = join(cheetah.__path__[0], "data")

        if not exists(datadir):
            makedirs(datadir)

        # copy the contents of our data source to datadir
        for r, ds, fs in walk(datasrc):
            for d in ds:
                rd = join(datadir, d)
                if not exists(rd):
                    makedirs(rd)
            for f in fs:
                rf = join(r, f)
                copy(rf, join(datadir, relpath(rf, datasrc)))

        # compose an extended list of the js and css files we copied
        # into place
        javascripts = list()
        stylesheets = list()

        for r, _ds, fs in walk(datadir):
            for f in fs:
                if f.endswith(".js"):
                    javascripts.append(join(r, f))
                elif f.endswith(".css"):
                    stylesheets.append(join(r, f))

        javascripts.extend(getattr(options, "html_javascripts", tuple()))
        stylesheets.extend(getattr(options, "html_stylesheets", tuple()))

        setattr(options, "html_javascripts", javascripts)
        setattr(options, "html_stylesheets", stylesheets)

        # keep from copying again
        setattr(options, "html_data_copied", True)


    def run_impl(self, change, entry, out):

        options = self.options
        crumbs = self.breadcrumbs

        # ensure we have copied data if we need to
        self.copy_data()

        # translate relative paths if necessary
        javascripts = self._relative_uris(options.html_javascripts)
        stylesheets = self._relative_uris(options.html_stylesheets)

        # create a transaction wrapping the output stream
        trans = CheetahStreamTransaction(out)
        
        # map the class of the change to a template class
        template_class = resolve_cheetah_template(type(change))

        # instantiate and setup the template
        template = template_class()
        template.transaction = trans
        template.change = change
        template.entry = entry
        template.options = options
        template.breadcrumbs = crumbs
        template.javascripts = javascripts
        template.stylesheets = stylesheets

        # this lets us call render_change from within the template on
        # a change instance to chain to another template (eg, for
        # sub-changes)
        rc = lambda c: self.run_impl(c, entry, out)
        template.render_change = rc

        # execute the template, which will write its contents to the
        # transaction (and the underlying stream)
        template.respond()

        # clean up the template
        template.shutdown()



class CheetahStreamTransaction(object):

    """ Transaction-like object for cheetah template instances which
    causes writes to go directly to a stream """

    def __init__(self, stream):
        self.stream = stream

    def response(self):
        return self.stream



def cheetah_template_map(cache=dict()):

    """ a map of change types to cheetah template types. Used in
    resolve_cheetah_template """

    from .cheetah import get_templates

    #pylint: disable=W0406
    # needed for introspection
    import javatools

    if cache:
        return cache    

    for template_type in get_templates():
        if not "_" in template_type.__name__:
            # we use the _ to denote package and class names. So any
            # template without a _ in the name isn't meant to be
            # matched to a change type.
            continue

        # get the package and change class names based off of the
        # template class name
        tn = template_type.__name__
        pn,cn = tn.split("_", 1)

        # get the package from javatools
        pk = getattr(javatools, pn, None)
        if pk is None:
            __import__("javatools."+pn)
            pk = getattr(javatools, pn, None)

        # get the class from the package
        cc = getattr(pk, cn, None)
        if cc is None:
            raise Exception("no change class for template %s" % tn)

        # associate a Change class with a Template class
        cache[cc] = template_type

    return cache



def resolve_cheetah_template(change_type):

    """ return the appropriate cheetah template class for the given
    change type, using the method-resolution-order of the change type.
    """

    tm = cheetah_template_map()

    # follow the built-in MRO for a type to find the matching
    # cheetah template
    for t in change_type.mro():
        tmpl = tm.get(t)
        if tmpl:
            return tmpl
    else:
        # this should never happen, since we'll provide a
        # change_Change template, and all of the changes should be
        # inheriting from that type
        raise Exception("No template for class %s" % change_type.__name__)



def html_report_optgroup(parser):

    """ Option group for the HTML report format """

    from optparse import OptionGroup

    g = OptionGroup(parser, "HTML Report Options")

    g.add_option("--html-stylesheet", action="append",
                 dest="html_stylesheets", default=list())

    g.add_option("--html-javascript", action="append", 
                 dest="html_javascripts", default=list())

    g.add_option("--html-copy-data", action="store", default=None,
                 help="Copy default resources to the given directory and"
                 " enable them in the template")

    return g



def quick_report(report_type, change, options):

    """ writes a change report via report_type to options.output or
    sys.stdout """

    from sys import stdout

    report = report_type(None, options)
    
    if options.output:
        with open(options.output, "wt") as out:
            report.run(change, None, out)
    else:
        report.run(change, None, stdout)



#
# The end.
