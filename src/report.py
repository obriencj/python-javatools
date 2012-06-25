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



class Reporter(object):


    def __init__(self, basedir, entry, options):
        self.basedir = basedir
        self.entry = entry
        self.options = options
        self.breadcrumbs = tuple()
        self.formats = list()


    def add_report_format(self, report_format):
        self.formats.append(report_format)


    def subreporter(self, subpath, entry):
        from os.path import join, relpath

        newbase = join(self.basedir, subpath)
        r = Reporter(newbase, entry, self.options)

        crumbs = [(relpath(a, newbase), b) for a, b in self.breadcrumbs]
        crumbs.append((relpath(self.basedir, newbase), self.entry))
        r.breadcrumbs = crumbs

        r.formats = list(self.formats)
        return r


    def run(self, change, out=None):

        basedir = self.basedir
        entry = self.entry
        options = self.options
        crumbs = self.breadcrumbs

        if out:
            for r in self.formats:
                r.run_impl(change, out, options, crumbs)

        else:
            for r in self.formats:
                r.run(change, basedir, entry, options, crumbs)



class ReportFormat(object):
    

    extension = ".report"


    def run_impl(self, change, out, options, breadcrumbs=tuple()):
        pass


    def run(self, change, basedir, entry, options, breadcrumbs=tuple()):
        from os.path import exists, join
        from os import makedirs
        from sys import stdout
        
        if basedir or entry:
            basedir = basedir or "./"
            entry = entry or "overall"
            
            if basedir and not exists(basedir):
                makedirs(basedir)

            fn = join(basedir, entry + self.extension)
            with open(fn, "wt") as out:
                self.run_impl(change, out, options, breadcrumbs)

            return fn

        else:
            self.run_impl(change, stdout, options)
            return None



def _opt_cb_report(_opt, _optstr, value, parser):
    options = parser.values
    
    if not hasattr(options, "reports"):
        options.reports = list()

    if "," in value:
        options.reports.extend(v for v in value.split(",") if v)
    else:
        options.reports.append(value)



def general_report_optgroup(parser):
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


    def run_impl(self, change, out, options, breadcrumbs=tuple()):
        from json import dump

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
    from optparse import OptionGroup

    g = OptionGroup(parser, "JON Report Options")

    g.add_option("--json-indent", action="store", default=2)

    return g



from json import JSONEncoder
class JSONChangeEncoder(JSONEncoder):

    """ A specialty JSONEncoder which knows how to represent Change
    instances (or anything with a simplify method) """

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


    def run_impl(self, change, out, options, breadcrumbs=tuple()):
        _indent_change(change, out, options, 0)



def _indent_change(change, out, options, indent):
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

    """ utility for use in writing change messages to a stream, using
    indentation to denote superchange children """

    for x in xrange(0,indent):
        stream.write("  ")
    for x in msgs:
        stream.write(x.encode("ascii", errors="backslashreplace"))
    stream.write("\n")



class CheetahReportFormat(ReportFormat):

    """ HTML output for a Change """
    
    extension = ".html"


    def run_impl(self, change, out, options, breadcrumbs=tuple()):
        trans = CheetahStreamTransaction(out)

        template_class = resolve_cheetah_template(type(change))

        template = template_class()
        template.transaction = trans
        template.change = change
        template.options = options
        template.breadcrumbs = breadcrumbs

        # this lets us call render_change from within the template on
        # a change instance to chain to another template (eg, for
        # sub-changes)
        rc = lambda c: self.run_impl(c, out, options, breadcrumbs)
        template.render_change = rc

        template.respond()



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
    from optparse import OptionGroup

    g = OptionGroup(parser, "HTML Report Options")

    g.add_option("--html-stylesheet", action="append",
                 dest="html_stylesheets", default=list())

    g.add_option("--html-javascript", action="append", 
                 dest="html_javascripts", default=list())

    g.add_option("--html-copy-data", action="store_true")
    g.add_option("--html-data-dir", action="store", default=None)

    return g



#
# The end.
