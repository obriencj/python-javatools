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



class Reporter():


    def __init__(self, basedir, entry, options):
        self.basedir = basedir
        self.entry = entry
        self.options = options
        self.formats = list()


    def add_report_format(self, report_format):
        self.formats.append(report_format)


    def subreporter(self, subpath, entry):
        from os.path import join
        r = Reporter(join(self.basedir, subpath), entry, self.options)
        r.formats = list(self.formats)
        return r


    def run(self, change, out=None):
        if out:
            for r in self.formats:
                r.run_impl(change, out, self.options)

        else:
            for r in self.formats:
                r.run(change, self.basedir, self.entry, self.options)



class ReportFormat():
    

    extension = ".report"


    def run_impl(self, change, out, options):
        pass


    def run(self, change, basedir, entry, options):
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
                self.run_impl(change, out, options)

            return fn

        else:
            self.run_impl(change, stdout, options)
            return None



class JSONReportFormat(ReportFormat):

    
    extension = ".json"


    def run_impl(self, change, out, options):
        from json import dump

        data = change.simplify(options)
        data["runtime_options"] = options.__dict__

        #print data
        dump(data, out, sort_keys=True, indent=2)

        

class TextReportFormat(ReportFormat):

    
    extension = ".text"


    def run_impl(self, change, out, options):
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



#
# The end.
