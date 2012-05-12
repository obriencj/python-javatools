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
Some abstraction of changes. Useful for the classdiff and jardiff
modules.

author: Christopher O'Brien  <obriencj@gmail.com>
license: LGPL
"""



def _indent(stream, indent, indentstr, *msgs):

    """ utility for use in writing change messages to a stream, using
    indentation to denote superchange children """

    for x in xrange(0,indent):
        stream.write(indentstr)
    for x in msgs:
        stream.write(x)
    stream.write("\n")



def yield_sorted_by_type(*typelist):
    """ a useful decorator for the collect_impl method of SuperChange
    subclasses. Caches the yielded changes, and re-emits them
    collected by their type. The order of the types can be specified
    by listing the types as arguments to this decorator. Unlisted
    types will be yielded last in no guaranteed order.

    Grouping happens by exact type match only. Inheritance is not
    taken into consideration for grouping. """

    def decorate(fun):
        cache = {}

        def decorated(*args,**kwds):
            # gather the emitted values by type
            for val in fun(*args, **kwds):
                key = val.__class__
                tl = cache.get(key, None)
                if not tl:
                    tl = list()
                    cache[key] = tl
                tl.append(val)

            # emit what we've gethered
            for t in typelist:
                for val in cache.pop(t, ()):
                    yield val

            # emit the leftovers
            for t,tl in cache.values():
                for val in tl:
                    yield val

        decorated.__doc__ = fun.__doc__
        decorated.func_name = fun.func_name
        decorated.func_doc = fun.func_doc
        return decorated
    return decorate



class Change(object):

    label = "Change"


    def __init__(self, ldata, rdata):
        self.ldata = ldata
        self.rdata = rdata
        self.description = None
        self.changed = False
        self.entry = None


    def clear(self):
        del self.ldata
        del self.rdata


    def check(self):
        pass


    def is_change(self):
        return self.changed


    def is_ignored(self, options):
        
        """ is this change ignorable, given parameters on the options
        object. """

        return False


    def get_description(self):
        return self.description or \
               (self.label + (" unchanged", " changed")[self.is_change()])


    def get_subchanges(self):
        return tuple()


    def simplify(self, options=None):

        """ returns a dict describing a simple snapshot of this
        change, and its children if any. """

        simple = {
            "class": type(self).__name__,
            "is_change": self.is_change(),
            "description": self.get_description(),
            "label": self.label,
            }

        if options:
            simple["is_ignored"] = self.is_ignored(options)

        if isinstance(self, Addition):
            simple["is_addition"] = True

        if isinstance(self, Removal):
            simple["is_removal"] = True

        if self.entry:
            simple["entry"] = self.entry

        # build a list of sub-changes honoring show-ignored and show-unchanged
        subs = list()
        for s in self.get_subchanges():
            if s.is_change():
                if options and s.is_ignored(options):
                    if getattr(options, "show_ignored", False):
                        subs.append(s)
                else:
                    subs.append(s)
            elif options and getattr(options, "show_unchanged", False):
                subs.append(s)

        if subs:
            simple["children"] = [s.simplify(options) for s in subs]

        return simple


    def write(self, options):
        import sys

        out = sys.stdout
        if options.output:
            out = open(options.output, "wt")

        if options.json:
            self.write_json(options, out)
        else:
            self.write_cli(options, 0, "  ", out)

        if options.output:
            out.close()


    def write_json(self, options, outstream):

        """ print JSON version of this change (from the simplify
        method) to the stream """

        from json import dump
        simple = self.simplify(options)
        simple["runtime_options"] = options.__dict__

        dump(simple, outstream, sort_keys=True, indent=2)
        

    def write_cli(self, options, indent, indentstr, outstream):

        """ print human-readable information about this change,
        including whether it was ignorable, etc. The options object
        provides parameters meaningful to individual change
        implementations. If outstream is None, the 'output' attribute
        of options may reference a file by name which will be opened
        for writing, or sys.stdout will be used."""

        show_unchanged = getattr(options, "show_unchanged", False)
        show_ignored = getattr(options, "show_ignored", False)

        show = False

        if self.is_change():
            if self.is_ignored(options):
                if show_ignored:
                    show = True
                    _indent(outstream,indent,indentstr,
                            self.get_description(), " [IGNORED]")
            else:
                show = True
                _indent(outstream,indent,indentstr,
                        self.get_description())
                
        elif show_unchanged:
            show = True
            _indent(outstream,indent,indentstr,
                    self.get_description())

        if show:
            for sub in self.get_subchanges():
                sub.write_cli(options, indent+1, indentstr, outstream)




class Removal(Change):

    """ Something was removed """

    def is_change(self):
        return True



class Addition(Change):
    
    """ Something was added """

    def is_change(self):
        return True



class GenericChange(Change):
    
    """ A generalized test for a single change on two objects: a left
    and a right. Subclasses should override the label and the check_impl """

    label = "Generic Change"


    def __init__(self, ldata, rdata):
        Change.__init__(self, ldata, rdata)
        self.changed = False


    def fn_data(self, c):
        
        """ Get the data to be used in fn_differ from c. By default,
        this method is the identity """

        return c


    def fn_pretty(self, c):
        """ override to provide a way to show the pretty version of the
        left or right data. Defaults to fn_data """

        return self.fn_data(c)

    
    def fn_pretty_desc(self, c):
        """ override to provide a way to describe the data left or right
        data. Defaults to fn_pretty """

        return self.fn_pretty(c)


    def fn_differ(self, ld, rd):
        """ override to provide the check for whether ld and rd differ.
        defaults to an equality check """

        return ld != rd


    def pretty_ldata(self):
        """ returns fn_pretty of ldata """

        return self.fn_pretty(self.ldata)


    def pretty_rdata(self):
        """ returns fn_pretty of rdata """

        return self.fn_pretty(self.rdata)


    def pretty_ldata_desc(self):
        """ returns fn_pretty_desc of ldata """

        return self.fn_pretty_desc(self.ldata)


    def pretty_rdata_desc(self):
        """ returns fn_pretty_desc of rdata """
        
        return self.fn_pretty_desc(self.rdata)


    def check_impl(self):

        """ returns a tuple of (is_change,description) which are then
        stored in self.changed and self.description

        The default implementation will get the data from the left and
        right sides by calling self.fn_data, then compare them via
        self.fn_differ. If they do differ, a message will be
        constructed using self.fn_pretty to create human-readable
        versions of the data that changed. """
        
        l, r = self.fn_data(self.ldata), self.fn_data(self.rdata)
        if self.fn_differ(l, r):
            l, r = self.pretty_ldata_desc(), self.pretty_rdata_desc()
            return True, "%s changed: %s to %s" % (self.label, l, r)
        else:
            return False, None


    def check(self):

        """ if necessary, override check_impl to change the behaviour of
        subclasses of GenericChange. """

        changed, msg = self.check_impl()
        self.changed = changed
        self.description = msg


    def simplify(self, options=None):
        simple = Change.simplify(self, options)

        simple["old_data"] = self.pretty_ldata()
        simple["new_data"] = self.pretty_rdata()
        
        return simple



class SuperChange(GenericChange):

    """ A collection of GenericChange instances """

    label = "Super Change"

    # override with change classes
    change_types = ()


    def __init__(self, ldata, rdata):
        GenericChange.__init__(self, ldata, rdata)
        self.changes = ()


    def clear(self):
        GenericChange.clear(self)
        for c in self.changes:
            c.clear()
        del self.changes


    def collect_impl(self):
        """ instanciates each of the entries in in the overriden
        change_types field with the left and right data, and collects
        the instances in self.changes """
        
        l, r = self.ldata, self.rdata
        return (c(l,r) for c in self.change_types)


    def check_impl(self):
        """ sets self.changes to the result of self.changes_impl, then
        if any member of those checks shows as a change, will return
        True,None """

        self.changes = tuple(self.collect_impl())
        
        c = False
        for change in self.changes:
            change.check()
            c = c or change.is_change()
        return c, None
            

    def is_ignored(self, options):
        if self.is_change():
            for change in self.changes:
                if change.is_change() and not change.is_ignored(options):
                    return False
            return True
        else:
            return False


    def get_subchanges(self):
        return self.changes


    def simplify(self, options=None):
        return Change.simplify(self, options)



class SquashedChange(Change):

    """ For when you want to keep just the overall data from a change,
    including whether it was ignored, but want to discard the more
    in-depth information. """

    def __init__(self, change, is_change, is_ignored):
        self.label = change.label
        self.description = change.get_description()
        self.changed = is_change
        self.ignored = is_ignored
        self.origclass = type(change)
        self.entry = getattr(change, "entry", None)

    def is_ignored(self, options):
        return self.ignored

    def is_change(self):
        return self.changed

    def simplify(self, options=None):
        simple = Change.simplify(self, options)
        simple["original_class"] = self.origclass.__name__
        return simple



class SquashedRemoval(SquashedChange, Removal):
    pass



class SquashedAddition(SquashedChange, Addition):
    pass



def squash(change, is_change, is_ignored):

    """ squashes the in-depth information of a change to a simplified
    (and less memory-intensive) form """

    if isinstance(change, Removal):
        return SquashedRemoval(change, is_change, is_ignored)
    elif isinstance(change, Addition):
        return SquashedAddition(change, is_change, is_ignored)
    else:
        return SquashedChange(change, is_change, is_ignored)



#
# The end.
